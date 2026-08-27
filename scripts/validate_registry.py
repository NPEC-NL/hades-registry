#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ALLOWED_RECORD_STATUS = {"active", "deprecated", "superseded", "draft", "internal_only"}
ALLOWED_REGISTRY_LAYER = {"authoring_template", "canonical_concrete"}
ALLOWED_MATERIALIZATION_RULES = {
    "concrete_only", "expand_stat", "expand_filter", "expand_filter_x_stat",
    "expand_band_x_stat", "matrix_no_expand",
}

REQUIRED_SOURCE_COLUMNS = [
    "variableId", "parent_variable_id", "parent_link_type", "registry_layer", "materialization_rule",
    "category", "subcategory", "variableName", "unit", "unit_accession", "value_type",
    "observation_level", "scaleName", "scaleClass", "system_id", "source_table_hint",
    "qc_recommended", "notes", "component", "core_nm", "in_bundle", "is_pattern",
    "pattern_band_values", "pattern_filter_values", "internal_codename_note", "filter_notes",
    "pattern_stat_values", "stat_axis_semantics", "acquisition_modality", "acquisition_filter",
    "acquisition_light_profile", "acquisition_geometry", "signal_interpretation", "roi_canonical",
    "implementation_roi_alias", "acquisition_unit", "axis_definition", "export_shape", "traitName",
    "traitAccNumber", "traitMappingConfidence", "traitEntity", "traitEntityAccessionNumber",
    "traitCharacteristic", "traitCharacteristicAccessionNumber", "methodName", "methodDesc",
    "methodRef", "record_status", "introduced_in_version", "deprecated_in_version",
    "replaced_by_variable_id",
]

REQUIRED_PUBLIC_CSV_COLUMNS = [
    "variableId", "parent_variable_id", "category", "subcategory", "variableName", "unit",
    "unit_accession", "value_type", "observation_level", "scaleName", "scaleClass", "system_id",
    "acquisition_modality", "acquisition_filter", "acquisition_light_profile", "acquisition_geometry",
    "signal_interpretation", "roi_canonical", "implementation_roi_alias", "acquisition_unit",
    "filter_notes", "axis_definition", "export_shape", "traitName", "traitAccNumber", "traitEntity",
    "traitEntityAccessionNumber", "traitCharacteristic", "traitCharacteristicAccessionNumber",
    "methodName", "methodDesc", "methodRef", "record_status", "introduced_in_version",
    "deprecated_in_version", "replaced_by_variable_id",
]

PUBLIC_RECORD_STATUS_EXCLUDE = {"draft", "internal_only"}
EXPECTED_VERSION = "0.1.0"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate the governed HADES variable registry.")
    p.add_argument("--source", default="variable_registry.source.csv")
    p.add_argument("--concrete", default="variable_registry.concrete.csv")
    p.add_argument("--public-concrete", default="variable_registry.public.concrete.csv")
    p.add_argument("--public-json", default="exports/public_registry.json")
    p.add_argument("--manifest", default="release_manifest.yaml")
    p.add_argument("--report", default="reports/validation_report.json")
    p.add_argument("--release-status", default="draft", choices=["draft", "release_candidate", "public"])
    return p.parse_args()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def bad_text(value: object) -> str | None:
    text = str(value or "")
    # Build known corruption tokens without embedding the corrupt glyphs or HTML
    # entities literally in this UTF-8 repository.
    checks = {
        "&" + "gt;": "HTML-escaped greater-than sign",
        "&" + "lt;": "HTML-escaped less-than sign",
        "\u00e2\u20ac\u201c": "mojibake en-dash",
        "\u00e2\u20ac\u201d": "mojibake em-dash",
        "\u00e2\u20ac\u00a6": "mojibake ellipsis",
        "\ufffd": "Unicode replacement character",
    }
    for token, label in checks.items():
        if token in text:
            return label
    return None


def family_rank(variable_id: str) -> int:
    if variable_id.startswith(("root.", "shoot.", "roi.")):
        return 0
    if variable_id.startswith("fluor."):
        return 1
    if variable_id.startswith("vnir."):
        return 2
    if variable_id.startswith("psi."):
        return 3
    if variable_id.startswith("seed."):
        return 4
    return 99


def validate_source(rows: list[dict[str, str]], fields: list[str], errors: list[str], warnings: list[str]) -> None:
    if not rows:
        errors.append("Source CSV missing or empty.")
        return

    missing = [column for column in REQUIRED_SOURCE_COLUMNS if column not in fields]
    if missing:
        errors.append("Missing required source columns: " + ", ".join(missing))

    obsolete = {"pattern_light_source_values", "light_source_names", "artifact_class", "variable_role"}
    present_obsolete = sorted(obsolete.intersection(fields))
    if present_obsolete:
        errors.append("Obsolete source columns remain: " + ", ".join(present_obsolete))

    previous_rank = -1
    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        variable_id = row.get("variableId", "")
        if variable_id in seen_ids:
            errors.append(f"Duplicate source variableId at row {row_number}: {variable_id}")
        seen_ids.add(variable_id)

        rank = family_rank(variable_id)
        if rank < previous_rank:
            errors.append(f"Source family order regression at row {row_number}: {variable_id}")
        previous_rank = max(previous_rank, rank)

        if row.get("record_status") not in ALLOWED_RECORD_STATUS:
            errors.append(f"Invalid record_status at source row {row_number}: {row.get('record_status')}")
        if row.get("registry_layer") not in ALLOWED_REGISTRY_LAYER:
            errors.append(f"Invalid registry_layer at source row {row_number}: {row.get('registry_layer')}")
        if row.get("materialization_rule") not in ALLOWED_MATERIALIZATION_RULES:
            errors.append(f"Invalid materialization_rule at source row {row_number}: {row.get('materialization_rule')}")
        if row.get("introduced_in_version") != EXPECTED_VERSION:
            errors.append(f"introduced_in_version must be {EXPECTED_VERSION} at source row {row_number}: {variable_id}")

        all_text = " | ".join(str(value or "") for value in row.values())
        problem = bad_text(all_text)
        if problem:
            errors.append(f"{problem} at source row {row_number}: {variable_id}")
        if "{light_source}" in all_text:
            errors.append(f"Obsolete {{light_source}} placeholder remains at source row {row_number}: {variable_id}")
        if "vnir.reflectance_spectrum" in all_text:
            errors.append(f"Obsolete VNIR reflectance naming remains at source row {row_number}: {variable_id}")
        if "vnir.pixel_spectra." in all_text:
            errors.append(f"Ambiguous generic VNIR pixel-spectra naming remains at source row {row_number}: {variable_id}")

        if row.get("registry_layer") == "canonical_concrete" and ("{" in variable_id or "}" in variable_id):
            errors.append(f"Concrete source row contains placeholder at row {row_number}: {variable_id}")
        if row.get("registry_layer") == "authoring_template" and "{" not in variable_id:
            warnings.append(f"Template source row has no placeholder at row {row_number}: {variable_id}")

        if variable_id.startswith("fluor."):
            if row.get("registry_layer") != "authoring_template":
                errors.append(f"FC source family must be authored as templates: {variable_id}")
            if row.get("materialization_rule") != "expand_filter_x_stat":
                errors.append(f"FC template must use expand_filter_x_stat: {variable_id}")
            if "{filter}" not in variable_id or "{stat}" not in variable_id:
                errors.append(f"FC template must contain {{filter}} and {{stat}}: {variable_id}")
            if "{filter}" not in row.get("system_id", ""):
                errors.append(f"FC system_id must carry the filter placeholder: {variable_id}")
            if row.get("acquisition_filter") != "{filter}":
                errors.append(f"FC acquisition_filter must be {{filter}} in source: {variable_id}")
            if row.get("acquisition_unit") != "derived_from_filter_capability":
                errors.append(f"FC acquisition_unit must be derived from filter capability: {variable_id}")
            if not row.get("acquisition_light_profile", "").strip():
                errors.append(f"FC acquisition_light_profile is required: {variable_id}")

        if variable_id.startswith("fluor.") and ".pixel_count.px" in variable_id:
            errors.append(f"FC pixel count must not be filter-expanded: {variable_id}")

        if variable_id.startswith("roi.") and variable_id.endswith(".pixel_count.px"):
            if row.get("acquisition_modality") != "rootcam_roi_mask":
                errors.append(f"ROI pixel count must be channel-independent rootcam_roi_mask: {variable_id}")
            if row.get("unit") != "px":
                errors.append(f"ROI pixel count unit must be px: {variable_id}")

        if variable_id.startswith("vnir.transmittance_spectrum."):
            if row.get("acquisition_geometry") != "transmission":
                errors.append(f"VNIR transmittance acquisition_geometry must be transmission: {variable_id}")
            if row.get("acquisition_modality") != "vnir_white_light_transmittance":
                errors.append(f"VNIR transmittance modality mismatch: {variable_id}")

        if variable_id.startswith(("vnir.emission_spectrum.", "vnir.emission_pixel_spectra.")):
            if row.get("acquisition_geometry") != "reflection":
                errors.append(f"VNIR fluorescence acquisition_geometry must be reflection: {variable_id}")
            if "365" not in row.get("acquisition_light_profile", ""):
                errors.append(f"VNIR fluorescence must record 365 nm UV excitation: {variable_id}")

        if variable_id.startswith("psi.vnir"):
            if row.get("acquisition_modality") != "psi_vendor_vnir":
                errors.append(f"PSI VNIR modality mismatch: {variable_id}")
            if row.get("traitEntity") != "plant" or row.get("traitEntityAccessionNumber") != "PO:0000003":
                errors.append(f"PSI VNIR trait entity must be plant / PO:0000003: {variable_id}")

    required_source_ids = {
        "roi.peri_root.pixel_count.px",
        "roi.root_plus_peri.pixel_count.px",
        "fluor.{filter}.peri_root.{stat}",
        "fluor.{filter}.root_plus_peri.{stat}",
        "vnir.transmittance_spectrum.root_350_900.{stat}.vector",
        "vnir.emission_spectrum.root_350_900.{stat}.vector",
        "vnir.emission_pixel_spectra.root_350_900.matrix",
        "seed.side",
        "seed.surface.mm2",
    }
    missing_ids = sorted(required_source_ids - seen_ids)
    if missing_ids:
        errors.append("Required 0.1.0 source rows missing: " + ", ".join(missing_ids))

    seed_ids = [row.get("variableId", "") for row in rows if row.get("variableId", "").startswith("seed.")]
    expected_seed_ids = [
        "seed.side", "seed.length.mm", "seed.ellipse_fit_sse", "seed.axes_angle.deg",
        "seed.width.mm", "seed.surface.mm2", "seed.pixel_count.px",
    ]
    if seed_ids != expected_seed_ids:
        errors.append("Boxeed source rows must match the seven raw measurement columns in raw-table order.")


def validate_concrete(rows: list[dict[str, str]], errors: list[str]) -> None:
    if not rows:
        errors.append("Concrete CSV missing or empty.")
        return

    seen: set[str] = set()
    previous_source_row = 0
    for row_number, row in enumerate(rows, start=2):
        variable_id = row.get("variableId", "")
        if variable_id in seen:
            errors.append(f"Duplicate concrete variableId: {variable_id}")
        seen.add(variable_id)
        if "{" in variable_id or "}" in variable_id:
            errors.append(f"Placeholder remains in concrete variableId: {variable_id}")

        all_text = " | ".join(str(value or "") for value in row.values())
        problem = bad_text(all_text)
        if problem:
            errors.append(f"{problem} in concrete row {row_number}: {variable_id}")
        if "{light_source}" in all_text:
            errors.append(f"Obsolete {{light_source}} placeholder remains in concrete: {variable_id}")
        if "vnir.reflectance_spectrum" in all_text:
            errors.append(f"Obsolete VNIR reflectance naming remains in concrete: {variable_id}")
        if variable_id.startswith("fluor.") and ".pixel_count.px" in variable_id:
            errors.append(f"Filter-specific FC pixel count remains in concrete registry: {variable_id}")

        source_row_number = int(row.get("source_row_number") or 0)
        if source_row_number and source_row_number < previous_source_row:
            errors.append(f"Concrete row order no longer follows source order at {variable_id}")
        previous_source_row = max(previous_source_row, source_row_number)

        if variable_id.startswith("fluor."):
            if row.get("acquisition_unit") not in {"FC1", "FC2", "FC1|FC2"}:
                errors.append(f"Concrete FC row has unresolved acquisition_unit: {variable_id}")
            if "{" in row.get("system_id", "") or "}" in row.get("system_id", ""):
                errors.append(f"Concrete FC system_id has unresolved placeholder: {variable_id}")

        if variable_id.endswith(".pixel_count.px") and row.get("unit") != "px":
            errors.append(f"Pixel-count unit policy violated for {variable_id}: {row.get('unit')}")


def validate_public(
    rows: list[dict[str, str]], fields: list[str], public_json: Path, release_status: str,
    errors: list[str], warnings: list[str],
) -> None:
    if release_status == "public":
        if not rows:
            errors.append("Public release requested but public concrete CSV is missing or empty.")
            return
        missing = [column for column in REQUIRED_PUBLIC_CSV_COLUMNS if column not in fields]
        if missing:
            errors.append("Missing required public CSV columns: " + ", ".join(missing))
        for row in rows:
            for required in ("variableId", "variableName", "unit", "value_type", "observation_level", "system_id", "methodName", "methodDesc"):
                if not str(row.get(required, "")).strip():
                    errors.append(f"Public row missing required field {required}: {row.get('variableId')}")
            problem = bad_text(" | ".join(str(value or "") for value in row.values()))
            if problem:
                errors.append(f"{problem} in public CSV: {row.get('variableId')}")
        if not public_json.exists():
            errors.append("Public release requested but public_registry.json is missing.")
        else:
            try:
                payload = json.loads(public_json.read_text(encoding="utf-8"))
                if not isinstance(payload.get("variables"), list):
                    errors.append("public_registry.json does not contain a variables list.")
            except Exception as exc:
                errors.append(f"Could not parse public_registry.json: {exc}")
    else:
        if rows or public_json.exists():
            warnings.append("Public artifacts exist although release_status is not public.")


def main() -> None:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    source_rows, source_fields = read_csv(Path(args.source))
    concrete_rows, _ = read_csv(Path(args.concrete))
    public_rows, public_fields = read_csv(Path(args.public_concrete))

    validate_source(source_rows, source_fields, errors, warnings)
    validate_concrete(concrete_rows, errors)
    validate_public(public_rows, public_fields, Path(args.public_json), args.release_status, errors, warnings)

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        errors.append("release_manifest.yaml is missing.")
    else:
        manifest = manifest_path.read_text(encoding="utf-8")
        if f"registry_version: {EXPECTED_VERSION}" not in manifest:
            errors.append(f"Manifest registry_version is not {EXPECTED_VERSION}.")
        if f"export_schema_version: {EXPECTED_VERSION}" not in manifest:
            errors.append(f"Manifest export_schema_version is not {EXPECTED_VERSION}.")
        if f"release_status: {args.release_status}" not in manifest:
            warnings.append("Manifest release_status does not match validation mode.")

    report = {
        "registry_version": EXPECTED_VERSION,
        "release_status": args.release_status,
        "source_rows": len(source_rows),
        "concrete_rows": len(concrete_rows),
        "errors": errors,
        "warnings": warnings,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)
    for warning in warnings:
        print("WARNING:", warning)
    print(f"Validation passed: {len(source_rows)} source rows -> {len(concrete_rows)} concrete rows.")


if __name__ == "__main__":
    main()
