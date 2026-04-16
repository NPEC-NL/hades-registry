\
#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

ALLOWED_RECORD_STATUS = {"active","deprecated","superseded","draft","internal_only"}
ALLOWED_REGISTRY_LAYER = {"authoring_template","canonical_concrete"}
REQUIRED_SOURCE_COLUMNS = [
    "variableId","parent_variable_id","parent_link_type","registry_layer","materialization_rule",
    "category","subcategory","variableName","unit","unit_accession","value_type","observation_level",
    "scaleName","scaleClass","system_id","source_table_hint","qc_recommended","notes","component",
    "core_nm","in_bundle","is_pattern","pattern_band_values","pattern_light_source_values",
    "light_source_names","pattern_filter_values","internal_codename_note","filter_notes",
    "pattern_stat_values","stat_axis_semantics","acquisition_modality","acquisition_filter",
    "signal_interpretation","roi_canonical","implementation_roi_alias","acquisition_unit",
    "axis_definition","export_shape","traitName","traitAccNumber","traitMappingConfidence",
    "traitEntity","traitEntityAccessionNumber","traitCharacteristic",
    "traitCharacteristicAccessionNumber","methodName","methodDesc","methodRef","record_status",
    "introduced_in_version","deprecated_in_version","replaced_by_variable_id"
]
REQUIRED_PUBLIC_CSV_COLUMNS = [
    "variableId","parent_variable_id","category","subcategory","variableName","unit","unit_accession",
    "value_type","observation_level","scaleName","scaleClass","system_id","acquisition_modality",
    "acquisition_filter","signal_interpretation","roi_canonical","implementation_roi_alias",
    "acquisition_unit","filter_notes","axis_definition","export_shape","traitName",
    "traitAccNumber","traitEntity","traitEntityAccessionNumber","traitCharacteristic",
    "traitCharacteristicAccessionNumber","methodName","methodDesc","methodRef","record_status",
    "introduced_in_version","deprecated_in_version","replaced_by_variable_id"
]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="variable_registry.source.csv")
    p.add_argument("--concrete", default="variable_registry.concrete.csv")
    p.add_argument("--public-concrete", default="variable_registry.public.concrete.csv")
    p.add_argument("--public-json", default="exports/public_registry.json")
    p.add_argument("--manifest", default="release_manifest.yaml")
    p.add_argument("--report", default="reports/validation_report.json")
    p.add_argument("--release-status", default="draft", choices=["draft","release_candidate","public"])
    return p.parse_args()

def read_csv(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))

def main():
    args = parse_args()
    errors, warnings = [], []

    source_rows = read_csv(Path(args.source))
    concrete_rows = read_csv(Path(args.concrete))
    public_rows = read_csv(Path(args.public_concrete))
    manifest_text = Path(args.manifest).read_text(encoding="utf-8") if Path(args.manifest).exists() else ""

    if not source_rows:
        errors.append("Source CSV missing or empty.")
    else:
        missing = [c for c in REQUIRED_SOURCE_COLUMNS if c not in source_rows[0]]
        if missing:
            errors.append("Missing required source columns: " + ", ".join(missing))
        for i, row in enumerate(source_rows, start=2):
            if row.get("record_status") not in ALLOWED_RECORD_STATUS:
                errors.append(f"Invalid record_status at source row {i}: {row.get('record_status')}")
            if row.get("registry_layer") not in ALLOWED_REGISTRY_LAYER:
                errors.append(f"Invalid registry_layer at source row {i}: {row.get('registry_layer')}")
            if row.get("registry_layer") == "authoring_template" and "{" not in row.get("variableId",""):
                warnings.append(f"Template row without placeholder at source row {i}: {row.get('variableId')}")
            if row.get("registry_layer") == "canonical_concrete" and "{" in row.get("variableId",""):
                errors.append(f"Concrete source row still contains placeholder at row {i}: {row.get('variableId')}")

    if not concrete_rows:
        errors.append("Concrete CSV missing or empty.")
    else:
        seen = set()
        for i, row in enumerate(concrete_rows, start=2):
            vid = row.get("variableId","")
            if vid in seen:
                errors.append(f"Duplicate concrete variableId: {vid}")
            seen.add(vid)
            if "{" in vid or "}" in vid:
                errors.append(f"Placeholder remained in concrete variableId: {vid}")
            if row.get("record_status") not in ALLOWED_RECORD_STATUS:
                errors.append(f"Invalid record_status in concrete row {i}: {row.get('record_status')}")
            if vid.endswith(".pixel_count.px") and row.get("unit") not in {"px","count"}:
                errors.append(f"Pixel count unit policy violated for {vid}: {row.get('unit')}")

    if args.release_status == "public":
        if not public_rows:
            errors.append("Public release requested but public concrete CSV missing.")
        else:
            missing = [c for c in REQUIRED_PUBLIC_CSV_COLUMNS if c not in public_rows[0]]
            if missing:
                errors.append("Missing required public CSV columns: " + ", ".join(missing))
        if not Path(args.public_json).exists():
            errors.append("Public release requested but public_registry.json missing.")
    else:
        if Path(args.public_json).exists() or Path(args.public_concrete).exists():
            warnings.append("Public artifacts exist even though release_status is not public.")

    if manifest_text and f"release_status: {args.release_status}" not in manifest_text:
        warnings.append("Manifest release_status does not match validation mode.")

    report = {"release_status": args.release_status, "errors": errors, "warnings": warnings}
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
