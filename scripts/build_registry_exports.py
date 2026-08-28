#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path

DEFAULT_REGISTRY_VERSION = "1.0.0"
DEFAULT_EXPORT_SCHEMA_VERSION = "1.0.0"
PUBLIC_RECORD_STATUS_EXCLUDE = {"draft", "internal_only"}

# Filter availability follows the two HADES RootCam/FluorCam units.  The unit is
# implementation metadata only and is not part of the canonical variableId.
FC_FILTER_UNITS = {
    "F448": "FC2",
    "F469": "FC1",
    "F483": "FC1",
    "F513": "FC1|FC2",
    "F520": "FC2",
    "F565": "FC1",
    "F586": "FC1",
    "F593": "FC1|FC2",
    "F635": "FC2",
    "ChlF": "FC2",
    "glass": "FC1|FC2",
}

PUBLIC_CSV_COLUMNS = [
    "variableId", "parent_variable_id", "category", "subcategory", "variableName",
    "unit", "unit_accession", "value_type", "observation_level", "scaleName", "scaleClass",
    "system_id", "acquisition_modality", "acquisition_filter", "acquisition_light_profile",
    "acquisition_geometry", "signal_interpretation", "roi_canonical", "implementation_roi_alias",
    "acquisition_unit", "filter_notes", "axis_definition", "export_shape", "traitName",
    "traitAccNumber", "traitEntity", "traitEntityAccessionNumber", "traitCharacteristic",
    "traitCharacteristicAccessionNumber", "methodName", "methodDesc", "methodRef",
    "record_status", "introduced_in_version", "deprecated_in_version", "replaced_by_variable_id",
]

DISPLAY_STAT = {
    "mean": "mean",
    "sum": "sum",
    "avg": "average",
    "median": "median",
    "min": "minimum",
    "max": "maximum",
    "std": "standard deviation",
    "stddev": "standard deviation",
}

ID_STAT = {
    "mean": "MEAN",
    "sum": "SUM",
    "avg": "AVG",
    "median": "MEDIAN",
    "min": "MIN",
    "max": "MAX",
    "std": "STD",
    "stddev": "STDDEV",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build HADES variable-registry exports from the authoritative source CSV.")
    p.add_argument("--source", default="variable_registry.source.csv")
    p.add_argument("--concrete", default="variable_registry.concrete.csv")
    p.add_argument("--public-concrete", default="variable_registry.public.concrete.csv")
    p.add_argument("--exports-dir", default="exports")
    p.add_argument("--public-json", default="exports/public_registry.json")
    p.add_argument("--manifest", default="release_manifest.yaml")
    p.add_argument("--checksums", default="checksums.sha256")
    p.add_argument("--registry-version", default=DEFAULT_REGISTRY_VERSION)
    p.add_argument("--export-schema-version", default=DEFAULT_EXPORT_SCHEMA_VERSION)
    p.add_argument("--source-commit", default=None)
    p.add_argument("--public-release-ready", default="false", choices=["true", "false"])
    p.add_argument("--release-status", default="draft", choices=["draft", "release_candidate", "public"])
    p.add_argument("--strict-public", action="store_true")
    return p.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def split_values(value: str | None) -> list[str]:
    seen: list[str] = []
    for part in str(value or "").split(","):
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return seen


def replace_placeholders(text: str | None, axes: dict[str, str], human: bool = False) -> str:
    out = str(text or "")
    for key, value in axes.items():
        replacement = DISPLAY_STAT.get(value, value) if human and key == "stat" else value
        out = out.replace("{" + key + "}", replacement)
    return out


def normalize_system_id(template: str | None, axes: dict[str, str]) -> str:
    out = replace_placeholders(template, axes, human=False)
    if "stat" in axes:
        token = ID_STAT.get(axes["stat"], axes["stat"].upper())
        out = re.sub(r"(?<![A-Z0-9])STAT(?![A-Z0-9])", token, out)
        out = re.sub(r"_STAT\b", "_" + token, out)
        out = re.sub(r":STAT\b", ":" + token, out)
    return out


def infer_export_shape(row: dict[str, str]) -> str:
    explicit = str(row.get("export_shape", "")).strip()
    if explicit:
        return explicit
    value_type = str(row.get("value_type", "")).strip()
    variable_id = str(row.get("variableId", "")).strip()
    if value_type.startswith("matrix") or variable_id.endswith(".matrix"):
        return "matrix"
    if value_type.startswith("array") or variable_id.endswith(".vector") or variable_id.endswith(".series"):
        return "vector"
    return "scalar"


def apply_effective_metadata(row: dict[str, str]) -> None:
    if not str(row.get("export_shape", "")).strip():
        row["export_shape"] = infer_export_shape(row)

    # The source template intentionally does not duplicate FC1/FC2 availability
    # for every filter.  Resolve it only in generated concrete rows.
    if row.get("acquisition_modality") == "fluorcam_single_channel":
        filt = str(row.get("acquisition_filter", "")).strip()
        if filt in FC_FILTER_UNITS and str(row.get("acquisition_unit", "")).strip() in {"", "derived_from_filter_capability"}:
            row["acquisition_unit"] = FC_FILTER_UNITS[filt]


def expansion_axes(row: dict[str, str]) -> list[dict[str, str]]:
    rule = str(row.get("materialization_rule", "") or "")
    stats = split_values(row.get("pattern_stat_values"))
    filters = split_values(row.get("pattern_filter_values"))
    bands = split_values(row.get("pattern_band_values"))

    if rule == "expand_band_x_stat":
        return [dict(band_nm=band, stat=stat) for band, stat in itertools.product(bands, stats)]
    if rule == "expand_filter_x_stat":
        return [dict(filter=filt, stat=stat) for filt, stat in itertools.product(filters, stats)]
    if rule == "expand_filter":
        return [dict(filter=filt) for filt in filters]
    if rule == "expand_stat":
        return [dict(stat=stat) for stat in stats]
    if rule == "matrix_no_expand":
        return [dict()]
    if rule == "concrete_only":
        return [dict()]
    raise ValueError(f"Unsupported materialization_rule: {rule!r} for {row.get('variableId')!r}")


def expand_source_rows(source_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    if not source_rows:
        return [], []

    fieldnames = list(source_rows[0].keys()) + ["template_variable_id", "expanded_axes_json", "source_row_number"]
    concrete: list[dict[str, str]] = []

    for source_row_number, row in enumerate(source_rows, start=2):
        is_template = row.get("registry_layer") == "authoring_template"
        axes_list = expansion_axes(row) if is_template else [dict()]

        for axes in axes_list:
            new = deepcopy(row)
            new["template_variable_id"] = row["variableId"] if is_template else ""
            new["expanded_axes_json"] = json.dumps(axes, sort_keys=True)
            new["source_row_number"] = str(source_row_number)

            if is_template:
                for col in list(new.keys()):
                    if col == "system_id":
                        new[col] = normalize_system_id(new.get(col), axes)
                    else:
                        new[col] = replace_placeholders(new.get(col), axes, human=True)
                # variableId must retain terse axis values rather than display labels.
                new["variableId"] = replace_placeholders(row["variableId"], axes, human=False)

            new["registry_layer"] = "canonical_concrete"
            new["materialization_rule"] = "concrete_only"
            new["is_pattern"] = "no"
            new["pattern_band_values"] = ""
            new["pattern_filter_values"] = ""
            new["pattern_stat_values"] = ""
            apply_effective_metadata(new)
            concrete.append(new)

    # Deliberately preserve source row order and, within templates, the pattern
    # axis order stated in the source CSV.  Never sort by variableId here.
    return concrete, fieldnames


def clean_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def to_internal_json_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        item: dict[str, object] = {}
        for key, value in row.items():
            if key == "expanded_axes_json":
                item["expanded_axes"] = json.loads(value or "{}")
            else:
                item[key] = value
        out.append(item)
    return out


def public_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [deepcopy(row) for row in rows if row.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE]


def to_public_csv_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [{column: row.get(column, "") for column in PUBLIC_CSV_COLUMNS} for row in rows]


def common_payload(row: dict[str, str]) -> dict[str, object]:
    return {
        "variableId": row["variableId"],
        "variableName": row["variableName"],
        "observationLevel": row.get("observation_level", ""),
        "traitName": clean_text(row.get("traitName")),
        "traitAccNumber": clean_text(row.get("traitAccNumber")),
        "traitEntity": clean_text(row.get("traitEntity")),
        "traitEntityAccessionNumber": clean_text(row.get("traitEntityAccessionNumber")),
        "traitCharacteristic": clean_text(row.get("traitCharacteristic")),
        "traitCharacteristicAccessionNumber": clean_text(row.get("traitCharacteristicAccessionNumber")),
        "methodName": clean_text(row.get("methodName")),
        "methodDescription": clean_text(row.get("methodDesc")),
        "methodReference": clean_text(row.get("methodRef")),
        "scaleName": clean_text(row.get("scaleName")),
        "scaleClass": clean_text(row.get("scaleClass")),
        "unit": row.get("unit", ""),
        "unitAccession": clean_text(row.get("unit_accession")),
        "systemId": row.get("system_id", ""),
        "category": row.get("category", ""),
        "subcategory": row.get("subcategory", ""),
        "roiCanonical": clean_text(row.get("roi_canonical")),
        "implementationRoiAlias": clean_text(row.get("implementation_roi_alias")),
        "signalInterpretation": clean_text(row.get("signal_interpretation")),
        "filterNotes": clean_text(row.get("filter_notes")),
        "acquisition": {
            "modality": clean_text(row.get("acquisition_modality")),
            "filter": clean_text(row.get("acquisition_filter")),
            "lightProfile": clean_text(row.get("acquisition_light_profile")),
            "geometry": clean_text(row.get("acquisition_geometry")),
            "unit": clean_text(row.get("acquisition_unit")),
        },
        "dataShape": {
            "exportShape": clean_text(row.get("export_shape")),
            "axisDefinition": clean_text(row.get("axis_definition")),
        },
        "status": {
            "recordStatus": row.get("record_status", ""),
            "introducedInVersion": row.get("introduced_in_version", ""),
            "deprecatedInVersion": clean_text(row.get("deprecated_in_version")),
            "replacedByVariableId": clean_text(row.get("replaced_by_variable_id")),
        },
        "notes": clean_text(row.get("notes")),
    }


def to_miappe(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    # Pragmatic MIAPPE-compatible bridge. HADES acquisition metadata remains in
    # local extension fields rather than pretending to be MIAPPE core terms.
    return [common_payload(row) for row in rows]


def to_brapi(rows: list[dict[str, str]], export_schema_version: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in rows:
        base = common_payload(row)
        out.append({
            "observationVariableDbId": base["variableId"],
            "observationVariableName": base["variableName"],
            "trait": {
                "traitName": base["traitName"],
                "traitDbId": base["traitAccNumber"],
                "entity": base["traitEntity"],
                "entityDbId": base["traitEntityAccessionNumber"],
                "attribute": base["traitCharacteristic"],
                "attributeDbId": base["traitCharacteristicAccessionNumber"],
            },
            "method": {
                "methodName": base["methodName"],
                "description": base["methodDescription"],
                "reference": base["methodReference"],
            },
            "scale": {
                "scaleName": base["scaleName"],
                "dataType": row.get("value_type", ""),
                "scaleClass": base["scaleClass"],
            },
            "contextOfUse": [row.get("observation_level", ""), row.get("category", ""), row.get("subcategory", "")],
            "ontologyReference": {"ontologyName": "MIAPPE-aligned local registry", "version": export_schema_version},
            "unit": row.get("unit", ""),
            "unitDbId": base["unitAccession"],
            "systemId": row.get("system_id", ""),
            "roiCanonical": base["roiCanonical"],
            "implementationRoiAlias": base["implementationRoiAlias"],
            "signalInterpretation": base["signalInterpretation"],
            "filterNotes": base["filterNotes"],
            "acquisition": base["acquisition"],
            "dataShape": base["dataShape"],
            "status": base["status"],
        })
    return out


def to_public_registry(rows: list[dict[str, str]], registry_version: str, export_schema_version: str) -> dict[str, object]:
    variables: list[dict[str, object]] = []
    for row in rows:
        base = common_payload(row)
        variables.append({
            "variableId": base["variableId"],
            "variableName": base["variableName"],
            "systemId": base["systemId"],
            "category": base["category"],
            "subcategory": base["subcategory"],
            "observationLevel": base["observationLevel"],
            "unit": base["unit"],
            "unitAccession": base["unitAccession"],
            "valueType": row.get("value_type", ""),
            "scale": {"scaleName": base["scaleName"], "scaleClass": base["scaleClass"]},
            "trait": {"name": base["traitName"], "accession": base["traitAccNumber"]},
            "traitEntity": {"name": base["traitEntity"], "accession": base["traitEntityAccessionNumber"]},
            "traitCharacteristic": {"name": base["traitCharacteristic"], "accession": base["traitCharacteristicAccessionNumber"]},
            "method": {"name": base["methodName"], "description": base["methodDescription"], "reference": base["methodReference"]},
            "roiCanonical": base["roiCanonical"],
            "implementationRoiAlias": base["implementationRoiAlias"],
            "signalInterpretation": base["signalInterpretation"],
            "filterNotes": base["filterNotes"],
            "acquisition": base["acquisition"],
            "dataShape": base["dataShape"],
            "status": base["status"],
        })
    return {
        "metadata": {
            "registry_version": registry_version,
            "export_schema_version": export_schema_version,
            "artifact": "public_registry.json",
            "public_identifier_policy": "Concrete variableId values in a public release are stable identifiers; later semantic replacements must use deprecation or supersession rather than silent renaming.",
        },
        "variables": variables,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    path: Path,
    registry_version: str,
    export_schema_version: str,
    release_status: str,
    generated_files: list[str],
    source_commit: str,
    public_release_ready: bool,
) -> None:
    lines = [
        f"registry_version: {registry_version}",
        f"export_schema_version: {export_schema_version}",
        f"release_date: '{date.today().isoformat()}'",
        "source_file: variable_registry.source.csv",
        f"source_commit: {source_commit}",
        f"release_status: {release_status}",
        f"public_release_ready: {str(public_release_ready).lower()}",
        "identifier_policy: public_stable_from_1.0.0",
        "generated_files:",
    ]
    lines.extend(f"  - {item}" for item in generated_files)
    lines.extend([
        "conditional_public_generated_files:",
        "  - variable_registry.public.concrete.csv",
        "  - exports/public_registry.json",
        "validation_flags:",
        "  require_concrete_ids_without_braces: true",
        "  require_public_artifacts_only_when_release_status_public: true",
        "  preserve_source_family_order: true",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checksums(path: Path, physical_to_logical: list[tuple[Path, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha256(physical)}  {logical}" for physical, logical in physical_to_logical if physical.exists()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    concrete_path = Path(args.concrete)
    public_concrete_path = Path(args.public_concrete)
    exports_dir = Path(args.exports_dir)
    public_json_path = Path(args.public_json)
    manifest_path = Path(args.manifest)
    checksums_path = Path(args.checksums)

    public_ready = args.public_release_ready == "true"
    if args.strict_public and (args.release_status != "public" or not public_ready):
        raise SystemExit("Strict public build requires --release-status public and --public-release-ready true.")

    source_rows = read_csv(source_path)
    concrete_rows, concrete_fields = expand_source_rows(source_rows)
    write_csv(concrete_path, concrete_rows, concrete_fields)

    source_commit = args.source_commit or f"registry-v{args.registry_version}-{args.release_status}"
    base_metadata = {
        "registry_version": args.registry_version,
        "export_schema_version": args.export_schema_version,
        "release_status": args.release_status,
        "source_commit": source_commit,
        "public_release_ready": public_ready,
    }

    internal_path = exports_dir / "internal_registry.json"
    miappe_path = exports_dir / "miappe_variables.json"
    brapi_path = exports_dir / "brapi_observation_variables.json"

    write_json(internal_path, {
        "metadata": base_metadata | {"artifact": "internal_registry.json"},
        "variables": to_internal_json_rows(concrete_rows),
    })
    write_json(miappe_path, {
        "metadata": base_metadata | {"artifact": "miappe_variables.json"},
        "variables": to_miappe(concrete_rows),
    })
    write_json(brapi_path, {
        "metadata": base_metadata | {"artifact": "brapi_observation_variables.json"},
        "variables": to_brapi(concrete_rows, args.export_schema_version),
    })

    generated_logical = [
        "variable_registry.concrete.csv",
        "exports/internal_registry.json",
        "exports/miappe_variables.json",
        "exports/brapi_observation_variables.json",
        "release_manifest.yaml",
        "checksums.sha256",
    ]

    if args.release_status == "public":
        public_rows_list = public_rows(concrete_rows)
        write_csv(public_concrete_path, to_public_csv_rows(public_rows_list), PUBLIC_CSV_COLUMNS)
        write_json(public_json_path, to_public_registry(public_rows_list, args.registry_version, args.export_schema_version))
        generated_logical.extend(["variable_registry.public.concrete.csv", "exports/public_registry.json"])
    else:
        # Remove stale public artifacts only at the paths explicitly supplied to
        # this build.  This makes temporary strict-public builds non-contaminating.
        for stale in (public_concrete_path, public_json_path):
            if stale.exists():
                stale.unlink()

    write_manifest(
        manifest_path,
        args.registry_version,
        args.export_schema_version,
        args.release_status,
        generated_logical,
        source_commit,
        public_ready,
    )

    # Do not hash checksums.sha256 into itself. Logical labels are canonical even
    # when a validation build writes to a temporary directory.
    physical_to_logical = [
        (source_path, "variable_registry.source.csv"),
        (concrete_path, "variable_registry.concrete.csv"),
        (internal_path, "exports/internal_registry.json"),
        (miappe_path, "exports/miappe_variables.json"),
        (brapi_path, "exports/brapi_observation_variables.json"),
        (manifest_path, "release_manifest.yaml"),
    ]
    if args.release_status == "public":
        physical_to_logical.extend([
            (public_concrete_path, "variable_registry.public.concrete.csv"),
            (public_json_path, "exports/public_registry.json"),
        ])
    write_checksums(checksums_path, physical_to_logical)


if __name__ == "__main__":
    main()
