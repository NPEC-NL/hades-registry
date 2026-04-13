#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List

ALLOWED_RECORD_STATUS = {"active", "deprecated", "superseded", "draft", "internal_only"}
ALLOWED_REGISTRY_LAYER = {"authoring_template", "canonical_concrete"}
ALLOWED_VARIABLE_ROLE = {
    "primary_trait",
    "observed_variable",
    "analysis_derived",
    "matrix_trait",
    "vendor_derived",
    "vendor_derived_matrix",
}
REQUIRED_SOURCE_COLUMNS = [
    "variableId",
    "parent_variable_id",
    "parent_link_type",
    "registry_layer",
    "materialization_rule",
    "category",
    "subcategory",
    "variableName",
    "unit",
    "unit_accession",
    "value_type",
    "observation_level",
    "scaleName",
    "scaleClass",
    "system_id",
    "source_table_hint",
    "qc_recommended",
    "notes",
    "component",
    "core_nm",
    "in_bundle",
    "is_pattern",
    "pattern_band_values",
    "pattern_stat_values",
    "stat_axis_semantics",
    "roi_class",
    "traitName",
    "traitAccNumber",
    "traitMappingConfidence",
    "traitEntity",
    "traitEntityAccessionNumber",
    "traitCharacteristic",
    "traitCharacteristicAccessionNumber",
    "methodName",
    "methodDesc",
    "methodRef",
    "variable_role",
    "record_status",
    "introduced_in_version",
    "deprecated_in_version",
    "replaced_by_variable_id",
    "manual_class",
]
REQUIRED_PUBLIC_CSV_COLUMNS = [
    "variableId",
    "parent_variable_id",
    "category",
    "subcategory",
    "variableName",
    "unit",
    "unit_accession",
    "value_type",
    "observation_level",
    "scaleName",
    "scaleClass",
    "system_id",
    "roi_class",
    "traitName",
    "traitAccNumber",
    "traitEntity",
    "traitEntityAccessionNumber",
    "traitCharacteristic",
    "traitCharacteristicAccessionNumber",
    "methodName",
    "methodDesc",
    "methodRef",
    "variable_role",
    "record_status",
    "introduced_in_version",
    "deprecated_in_version",
    "replaced_by_variable_id",
]
SOURCE_ONLY_COLUMNS = {
    "registry_layer",
    "materialization_rule",
    "source_table_hint",
    "qc_recommended",
    "component",
    "core_nm",
    "in_bundle",
    "is_pattern",
    "pattern_band_values",
    "pattern_stat_values",
    "stat_axis_semantics",
    "manual_class",
    "template_variable_id",
    "expanded_axes_json",
    "source_row_number",
    "traitMappingConfidence",
}
PUBLIC_RECORD_STATUS_EXCLUDE = {"draft", "internal_only"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate registry source and generated artifacts")
    parser.add_argument("--source", default="variable_registry.source.csv")
    parser.add_argument("--concrete", default="variable_registry.concrete.csv")
    parser.add_argument("--public-concrete", default="variable_registry.public.concrete.csv")
    parser.add_argument("--public-json", default="exports/public_registry.json")
    parser.add_argument("--manifest", default="release_manifest.yaml")
    parser.add_argument("--report", default="reports/validation_report.json")
    parser.add_argument("--release-status", default="draft", choices=["draft", "release_candidate", "public"])
    return parser.parse_args()


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def has_manual(value: str | None) -> bool:
    return "[MANUAL]" in str(value or "")


def split_values(value: str | None) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def check(condition: bool, errors: List[Dict[str, object]], *, type_: str, **payload: object) -> None:
    if not condition:
        data = {"type": type_}
        data.update(payload)
        errors.append(data)


def validate_source(source_rows: List[Dict[str, str]]) -> Dict[str, object]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []
    info: List[Dict[str, object]] = []

    if not source_rows:
        return {"errors": [{"type": "missing_or_empty_source_csv"}], "warnings": warnings, "info": info}

    header = list(source_rows[0].keys())
    check(header == REQUIRED_SOURCE_COLUMNS, errors, type_="source_columns_mismatch", expected=REQUIRED_SOURCE_COLUMNS, actual=header)

    seen = set()
    duplicates = set()
    public_manual_hits = []

    for idx, row in enumerate(source_rows, start=2):
        vid = row.get("variableId", "")
        if vid in seen:
            duplicates.add(vid)
        seen.add(vid)

        if row.get("registry_layer") not in ALLOWED_REGISTRY_LAYER:
            errors.append({"type": "invalid_registry_layer", "row": idx, "variableId": vid, "value": row.get("registry_layer")})
        if row.get("record_status") not in ALLOWED_RECORD_STATUS:
            errors.append({"type": "invalid_record_status", "row": idx, "variableId": vid, "value": row.get("record_status")})
        if row.get("variable_role") not in ALLOWED_VARIABLE_ROLE:
            errors.append({"type": "invalid_variable_role", "row": idx, "variableId": vid, "value": row.get("variable_role")})
        if row.get("record_status") == "superseded" and not str(row.get("replaced_by_variable_id", "")).strip():
            errors.append({"type": "superseded_without_replacement", "row": idx, "variableId": vid})
        if row.get("record_status") in {"deprecated", "superseded"} and not str(row.get("deprecated_in_version", "")).strip():
            errors.append({"type": "deprecated_without_version", "row": idx, "variableId": vid})

        is_pattern = str(row.get("is_pattern", "")).strip().lower() == "yes"
        if row.get("registry_layer") == "authoring_template" and not is_pattern:
            errors.append({"type": "template_row_missing_pattern_flag", "row": idx, "variableId": vid})
        if is_pattern and "{" not in vid:
            errors.append({"type": "pattern_without_placeholder", "row": idx, "variableId": vid})
        if not is_pattern and ("{" in vid or "}" in vid):
            errors.append({"type": "concrete_id_contains_braces_in_source", "row": idx, "variableId": vid})

        if row.get("registry_layer") == "authoring_template":
            rule = row.get("materialization_rule")
            if rule == "expand_stat":
                if not split_values(row.get("pattern_stat_values")):
                    errors.append({"type": "expand_stat_missing_pattern_stat_values", "row": idx, "variableId": vid})
                if "{stat}" not in vid:
                    errors.append({"type": "expand_stat_missing_stat_placeholder", "row": idx, "variableId": vid})
            elif rule == "expand_band_x_stat":
                if not split_values(row.get("pattern_stat_values")) or not split_values(row.get("pattern_band_values")):
                    errors.append({"type": "expand_band_x_stat_missing_axis_values", "row": idx, "variableId": vid})
                if "{stat}" not in vid or "{band_nm}" not in vid:
                    errors.append({"type": "expand_band_x_stat_missing_placeholders", "row": idx, "variableId": vid})
            elif rule != "concrete_only":
                warnings.append({"type": "unexpected_template_materialization_rule", "row": idx, "variableId": vid, "value": rule})

        if any(has_manual(v) for v in row.values()) and not str(row.get("manual_class", "")).strip():
            errors.append({"type": "manual_placeholder_without_manual_class", "row": idx, "variableId": vid})

        if row.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE:
            manual_fields = [k for k, v in row.items() if has_manual(v) and k not in SOURCE_ONLY_COLUMNS]
            if manual_fields:
                public_manual_hits.append({"row": idx, "variableId": vid, "fields": manual_fields})

        if "pixel_count" in vid:
            expected = {
                "unit": "px",
                "traitCharacteristic": "count",
                "variable_role": "analysis_derived",
            }
            for field, expected_value in expected.items():
                actual = str(row.get(field, "") or "").strip()
                if actual != expected_value:
                    errors.append({
                        "type": "pixel_count_semantics_mismatch",
                        "row": idx,
                        "variableId": vid,
                        "field": field,
                        "expected": expected_value,
                        "actual": actual,
                    })

    if duplicates:
        errors.append({"type": "duplicate_source_variableId", "variableIds": sorted(duplicates)})

    info.append({
        "type": "row_counts",
        "source_rows": len(source_rows),
        "template_rows": sum(1 for r in source_rows if r.get("registry_layer") == "authoring_template"),
        "concrete_rows_in_source": sum(1 for r in source_rows if r.get("registry_layer") == "canonical_concrete"),
        "public_source_rows": sum(1 for r in source_rows if r.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE),
    })
    info.append({"type": "public_manual_blockers_preview", "count": len(public_manual_hits)})
    if public_manual_hits:
        warnings.append({"type": "public_release_currently_blocked_by_manual_placeholders", "examples": public_manual_hits[:10]})
    return {"errors": errors, "warnings": warnings, "info": info}


def validate_concrete(concrete_rows: List[Dict[str, str]]) -> Dict[str, object]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []
    info: List[Dict[str, object]] = []

    if not concrete_rows:
        return {"errors": [{"type": "missing_or_empty_concrete_csv"}], "warnings": warnings, "info": info}

    seen = set()
    duplicates = set()
    for row in concrete_rows:
        vid = row.get("variableId", "")
        if vid in seen:
            duplicates.add(vid)
        seen.add(vid)
        if "{" in vid or "}" in vid:
            errors.append({"type": "brace_in_concrete_id", "variableId": vid})
        if row.get("registry_layer") != "canonical_concrete":
            errors.append({"type": "non_canonical_registry_layer_in_concrete", "variableId": vid, "value": row.get("registry_layer")})
        if str(row.get("is_pattern", "")).strip().lower() == "yes":
            errors.append({"type": "pattern_row_leaked_to_concrete", "variableId": vid})
        if row.get("record_status") not in ALLOWED_RECORD_STATUS:
            errors.append({"type": "invalid_record_status_in_concrete", "variableId": vid, "value": row.get("record_status")})
        if row.get("variable_role") not in ALLOWED_VARIABLE_ROLE:
            errors.append({"type": "invalid_variable_role_in_concrete", "variableId": vid, "value": row.get("variable_role")})
        if row.get("record_status") == "superseded" and not str(row.get("replaced_by_variable_id", "")).strip():
            errors.append({"type": "superseded_without_replacement", "variableId": vid})
        if row.get("record_status") in {"deprecated", "superseded"} and not str(row.get("deprecated_in_version", "")).strip():
            errors.append({"type": "deprecated_without_version", "variableId": vid})

    if duplicates:
        errors.append({"type": "duplicate_concrete_variableId", "variableIds": sorted(duplicates)})

    public_rows = [r for r in concrete_rows if r.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE]
    info.append({"type": "row_counts", "concrete_rows": len(concrete_rows), "public_rows": len(public_rows)})
    return {"errors": errors, "warnings": warnings, "info": info}


def validate_public_release(source_rows: List[Dict[str, str]], concrete_rows: List[Dict[str, str]], public_concrete_path: Path, public_json_path: Path, release_status: str) -> Dict[str, object]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []
    info: List[Dict[str, object]] = []

    expected_public_rows = [r for r in concrete_rows if r.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE]
    expected_ids = sorted(r["variableId"] for r in expected_public_rows)
    if release_status != "public":
        info.append({"type": "public_validation_mode", "status": "preview_only"})
        return {"errors": errors, "warnings": warnings, "info": info}

    check(public_concrete_path.exists(), errors, type_="missing_public_concrete_csv", path=str(public_concrete_path))
    check(public_json_path.exists(), errors, type_="missing_public_registry_json", path=str(public_json_path))
    if not public_concrete_path.exists() or not public_json_path.exists():
        return {"errors": errors, "warnings": warnings, "info": info}

    public_rows = read_csv(public_concrete_path)
    public_header = list(public_rows[0].keys()) if public_rows else []
    check(public_header == REQUIRED_PUBLIC_CSV_COLUMNS, errors, type_="public_csv_columns_mismatch", expected=REQUIRED_PUBLIC_CSV_COLUMNS, actual=public_header)

    for row in public_rows:
        vid = row.get("variableId", "")
        if "{" in vid or "}" in vid:
            errors.append({"type": "brace_in_public_concrete_id", "variableId": vid})
        for key, value in row.items():
            if has_manual(value):
                errors.append({"type": "manual_placeholder_in_public_concrete", "variableId": vid, "field": key})

    actual_ids = sorted(r["variableId"] for r in public_rows)
    check(actual_ids == expected_ids, errors, type_="public_concrete_id_set_mismatch")

    payload = json.loads(public_json_path.read_text(encoding="utf-8"))
    variables = payload.get("variables", [])
    json_ids = sorted(v.get("variableId") for v in variables)
    check(json_ids == expected_ids, errors, type_="public_json_id_set_mismatch")
    encoded = json.dumps(payload, ensure_ascii=False)
    check("[MANUAL]" not in encoded, errors, type_="manual_placeholder_in_public_json")

    forbidden_columns = [c for c in SOURCE_ONLY_COLUMNS if c in public_header]
    check(not forbidden_columns, errors, type_="source_only_columns_leaked_to_public_csv", columns=forbidden_columns)

    info.append({"type": "public_row_counts", "public_rows": len(public_rows)})
    return {"errors": errors, "warnings": warnings, "info": info}


def read_simple_yaml(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        key = key.strip()
        if key in {"generated_files", "conditional_public_generated_files", "validation_flags"}:
            continue
        data[key] = value.strip().strip("'\"")
    return data


def validate_manifest(manifest_path: Path, release_status: str) -> Dict[str, object]:
    errors: List[Dict[str, object]] = []
    warnings: List[Dict[str, object]] = []
    info: List[Dict[str, object]] = []
    if not manifest_path.exists():
        return {"errors": [{"type": "missing_manifest", "path": str(manifest_path)}], "warnings": warnings, "info": info}
    manifest = read_simple_yaml(manifest_path)
    source_commit = manifest.get("source_commit", "")
    public_release_ready = manifest.get("public_release_ready", "").lower()
    manifest_release_status = manifest.get("release_status", "")
    registry_version = manifest.get("registry_version", "")
    export_schema_version = manifest.get("export_schema_version", "")
    if not source_commit:
        errors.append({"type": "missing_source_commit"})
    if public_release_ready not in {"true", "false"}:
        errors.append({"type": "invalid_public_release_ready", "value": manifest.get("public_release_ready")})
    if manifest_release_status and manifest_release_status != release_status:
        errors.append({"type": "manifest_release_status_mismatch", "manifest": manifest_release_status, "arg": release_status})
    if public_release_ready == "true" and release_status != "public":
        errors.append({"type": "public_release_ready_requires_public_status"})
    if registry_version != "0.0.1":
        errors.append({"type": "unexpected_registry_version", "value": registry_version})
    if export_schema_version != "0.0.1":
        errors.append({"type": "unexpected_export_schema_version", "value": export_schema_version})
    info.append({"type": "manifest_values", "source_commit": source_commit, "public_release_ready": public_release_ready})
    return {"errors": errors, "warnings": warnings, "info": info}


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    concrete_path = Path(args.concrete)
    public_concrete_path = Path(args.public_concrete)
    public_json_path = Path(args.public_json)
    manifest_path = Path(args.manifest)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    source_rows = read_csv(source_path)
    concrete_rows = read_csv(concrete_path)

    report = {
        "release_status": args.release_status,
        "manifest": validate_manifest(manifest_path, args.release_status),
        "source": validate_source(source_rows),
        "concrete": validate_concrete(concrete_rows),
        "public_release": validate_public_release(source_rows, concrete_rows, public_concrete_path, public_json_path, args.release_status),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    has_errors = any(report[section]["errors"] for section in ["manifest", "source", "concrete", "public_release"])
    if has_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
