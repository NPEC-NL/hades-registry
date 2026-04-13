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
from typing import Dict, Iterable, List, Tuple

DEFAULT_REGISTRY_VERSION = "0.0.1"
DEFAULT_EXPORT_SCHEMA_VERSION = "0.0.1"
PUBLIC_RECORD_STATUS_EXCLUDE = {"draft", "internal_only"}

PUBLIC_CSV_COLUMNS = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build concrete and JSON exports from variable_registry.source.csv")
    parser.add_argument("--source", default="variable_registry.source.csv")
    parser.add_argument("--concrete", default="variable_registry.concrete.csv")
    parser.add_argument("--exports-dir", default="exports")
    parser.add_argument("--manifest", default="release_manifest.yaml")
    parser.add_argument("--checksums", default="checksums.sha256")
    parser.add_argument("--registry-version", default=DEFAULT_REGISTRY_VERSION)
    parser.add_argument("--export-schema-version", default=DEFAULT_EXPORT_SCHEMA_VERSION)
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--public-release-ready", default="false", choices=["true", "false"])
    parser.add_argument("--release-status", default="draft", choices=["draft", "release_candidate", "public"])
    parser.add_argument("--strict-public", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_values(value: str | None) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def replace_placeholders(text: str | None, axes: Dict[str, str], *, human: bool = False) -> str:
    out = str(text or "")
    for key, value in axes.items():
        replacement = DISPLAY_STAT.get(value, value) if human and key == "stat" else value
        out = out.replace("{" + key + "}", replacement)
    return out


def normalize_system_id(template: str, axes: Dict[str, str]) -> str:
    out = replace_placeholders(template, axes, human=False)
    if "stat" in axes:
        token = ID_STAT.get(axes["stat"], axes["stat"].upper())
        out = re.sub(r"(?<![A-Z0-9])STAT(?![A-Z0-9])", token, out)
        out = re.sub(r"_STAT\b", f"_{token}", out)
        out = re.sub(r":STAT\b", f":{token}", out)
    return out


def strip_template_notes(notes: str, template_variable_id: str, axes: Dict[str, str]) -> str:
    text = notes or ""
    text = re.sub(r"Pattern row\.[^.]*\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Pattern variable\.[^.]*\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Authoring-layer template row; expand to concrete variable IDs before downstream export\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    provenance = f"Expanded from template {template_variable_id} with axes {json.dumps(axes, sort_keys=True)}."
    return (text + " " + provenance).strip() if text else provenance


def infer_scale_name(unit: str, value_type: str) -> str:
    if value_type == "bool":
        return "boolean"
    return unit


def infer_scale_class(value_type: str) -> str:
    if value_type == "bool":
        return "Nominal"
    return "Numerical"


def apply_effective_scale(row: Dict[str, str]) -> None:
    if not str(row.get("scaleName", "")).strip():
        row["scaleName"] = infer_scale_name(str(row.get("unit", "")).strip(), str(row.get("value_type", "")).strip())
    if not str(row.get("scaleClass", "")).strip():
        row["scaleClass"] = infer_scale_class(str(row.get("value_type", "")).strip())


def expand_source_rows(source_rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[str]]:
    fieldnames = list(source_rows[0].keys()) + ["template_variable_id", "expanded_axes_json", "source_row_number"]
    concrete: List[Dict[str, str]] = []
    for idx, row in enumerate(source_rows, start=2):
        is_pattern = (row.get("registry_layer") == "authoring_template") or (str(row.get("is_pattern", "")).strip().lower() == "yes")
        if is_pattern:
            rule = row.get("materialization_rule", "")
            stat_values = split_values(row.get("pattern_stat_values"))
            band_values = split_values(row.get("pattern_band_values"))
            if rule == "expand_band_x_stat":
                axes_iter = [dict(band_nm=b, stat=s) for b, s in itertools.product(band_values, stat_values)]
            elif rule == "expand_stat":
                axes_iter = [dict(stat=s) for s in stat_values]
            else:
                axes_iter = [dict()]
            for axes in axes_iter:
                new = deepcopy(row)
                new["template_variable_id"] = row["variableId"]
                new["expanded_axes_json"] = json.dumps(axes, sort_keys=True)
                new["source_row_number"] = str(idx)
                for col in list(new.keys()):
                    if col == "system_id":
                        new[col] = normalize_system_id(new.get(col, ""), axes)
                    elif col == "notes":
                        new[col] = strip_template_notes(new.get(col, ""), row["variableId"], axes)
                    else:
                        new[col] = replace_placeholders(new.get(col, ""), axes, human=True)
                new["variableId"] = replace_placeholders(row["variableId"], axes, human=False)
                new["registry_layer"] = "canonical_concrete"
                new["materialization_rule"] = "concrete_only"
                new["is_pattern"] = "no"
                new["pattern_band_values"] = ""
                new["pattern_stat_values"] = ""
                apply_effective_scale(new)
                concrete.append(new)
        else:
            new = deepcopy(row)
            new["template_variable_id"] = ""
            new["expanded_axes_json"] = "{}"
            new["source_row_number"] = str(idx)
            new["registry_layer"] = "canonical_concrete"
            new["materialization_rule"] = "concrete_only"
            new["is_pattern"] = "no"
            new["pattern_band_values"] = ""
            new["pattern_stat_values"] = ""
            apply_effective_scale(new)
            concrete.append(new)
    concrete.sort(key=lambda r: r["variableId"])
    return concrete, fieldnames


def sanitize_export_text(value: str | None) -> str | None:
    text = str(value or "").replace("[MANUAL]", " ")
    text = re.sub(r"\s+", " ", text).strip(" ;,")
    return text or None


def clean_optional(value: str | None) -> str | None:
    return sanitize_export_text(value)


def to_internal_json_rows(concrete_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in concrete_rows:
        item: Dict[str, object] = {}
        for key, value in row.items():
            if key == "expanded_axes_json":
                item["expanded_axes"] = json.loads(value or "{}")
            else:
                item[key] = value
        item["manual_review"] = {k: v for k, v in row.items() if "[MANUAL]" in str(v or "")}
        out.append(item)
    return out


def public_concrete_rows(concrete_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rows = [deepcopy(r) for r in concrete_rows if r.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE]
    rows.sort(key=lambda r: r["variableId"])
    return rows


def to_public_csv_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [{col: row.get(col, "") for col in PUBLIC_CSV_COLUMNS} for row in rows]


def to_miappe_json_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "variableId": row["variableId"],
                "variableName": row["variableName"],
                "observationLevel": row["observation_level"],
                "traitName": clean_optional(row.get("traitName")),
                "traitAccNumber": clean_optional(row.get("traitAccNumber")),
                "traitEntity": clean_optional(row.get("traitEntity")),
                "traitEntityAccessionNumber": clean_optional(row.get("traitEntityAccessionNumber")),
                "traitCharacteristic": clean_optional(row.get("traitCharacteristic")),
                "traitCharacteristicAccessionNumber": clean_optional(row.get("traitCharacteristicAccessionNumber")),
                "methodName": clean_optional(row.get("methodName")),
                "methodDescription": clean_optional(row.get("methodDesc")),
                "methodReference": clean_optional(row.get("methodRef")),
                "scaleName": clean_optional(row.get("scaleName")),
                "scaleClass": clean_optional(row.get("scaleClass")),
                "unit": row["unit"],
                "unitAccession": clean_optional(row.get("unit_accession")),
                "valueType": row["value_type"],
                "systemId": row["system_id"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "roiClass": clean_optional(row.get("roi_class")),
                "variableRole": row["variable_role"],
                "status": {
                    "recordStatus": row["record_status"],
                    "introducedInVersion": row["introduced_in_version"],
                    "deprecatedInVersion": clean_optional(row.get("deprecated_in_version")),
                    "replacedByVariableId": clean_optional(row.get("replaced_by_variable_id")),
                },
                "notes": clean_optional(row.get("notes")),
            }
        )
    return out


def to_brapi_json_rows(rows: List[Dict[str, str]], export_schema_version: str) -> List[Dict[str, object]]:
    data: List[Dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "observationVariableDbId": row["variableId"],
                "observationVariableName": row["variableName"],
                "trait": {
                    "traitName": clean_optional(row.get("traitName")),
                    "traitDbId": clean_optional(row.get("traitAccNumber")),
                    "entity": clean_optional(row.get("traitEntity")),
                    "entityDbId": clean_optional(row.get("traitEntityAccessionNumber")),
                    "attribute": clean_optional(row.get("traitCharacteristic")),
                    "attributeDbId": clean_optional(row.get("traitCharacteristicAccessionNumber")),
                },
                "method": {
                    "methodName": clean_optional(row.get("methodName")),
                    "description": clean_optional(row.get("methodDesc")),
                    "reference": clean_optional(row.get("methodRef")),
                },
                "scale": {
                    "scaleName": clean_optional(row.get("scaleName")),
                    "dataType": row["value_type"],
                    "validValues": None,
                    "scaleClass": clean_optional(row.get("scaleClass")),
                },
                "contextOfUse": [row["observation_level"], row["category"], row["subcategory"]],
                "ontologyReference": {
                    "documentationLinks": [],
                    "ontologyName": "MIAPPE-aligned local registry",
                    "version": export_schema_version,
                },
                "unit": row["unit"],
                "unitDbId": clean_optional(row.get("unit_accession")),
                "systemId": row["system_id"],
                "variableRole": row["variable_role"],
                "roiClass": clean_optional(row.get("roi_class")),
            }
        )
    return data


def to_public_registry_json(rows: List[Dict[str, str]], registry_version: str, export_schema_version: str) -> Dict[str, object]:
    return {
        "metadata": {
            "registry_version": registry_version,
            "export_schema_version": export_schema_version,
            "artifact": "public_registry.json",
            "public_identifier_policy": "Concrete variableId values in this artifact are treated as stable public identifiers.",
        },
        "variables": [
            {
                "variableId": row["variableId"],
                "variableName": row["variableName"],
                "systemId": row["system_id"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "observationLevel": row["observation_level"],
                "unit": row["unit"],
                "unitAccession": clean_optional(row.get("unit_accession")),
                "valueType": row["value_type"],
                "scale": {"scaleName": clean_optional(row.get("scaleName")), "scaleClass": clean_optional(row.get("scaleClass"))},
                "trait": {"name": clean_optional(row.get("traitName")), "accession": clean_optional(row.get("traitAccNumber"))},
                "traitEntity": {"name": clean_optional(row.get("traitEntity")), "accession": clean_optional(row.get("traitEntityAccessionNumber"))},
                "traitCharacteristic": {"name": clean_optional(row.get("traitCharacteristic")), "accession": clean_optional(row.get("traitCharacteristicAccessionNumber"))},
                "method": {"name": clean_optional(row.get("methodName")), "description": clean_optional(row.get("methodDesc")), "reference": clean_optional(row.get("methodRef"))},
                "roiClass": clean_optional(row.get("roi_class")),
                "variableRole": row["variable_role"],
                "status": {
                    "recordStatus": row["record_status"],
                    "introducedInVersion": row["introduced_in_version"],
                    "deprecatedInVersion": clean_optional(row.get("deprecated_in_version")),
                    "replacedByVariableId": clean_optional(row.get("replaced_by_variable_id")),
                },
            }
            for row in rows
        ],
    }


def any_manual_in_rows(rows: Iterable[Dict[str, str]], columns: Iterable[str] | None = None) -> List[Tuple[str, str]]:
    problems: List[Tuple[str, str]] = []
    cols = list(columns) if columns is not None else None
    for row in rows:
        for key, value in row.items():
            if cols is not None and key not in cols:
                continue
            if "[MANUAL]" in str(value or ""):
                problems.append((row.get("variableId", ""), key))
    return problems


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, *, registry_version: str, export_schema_version: str, release_status: str, generated_files: List[str], source_commit: str, public_release_ready: bool) -> None:
    public_supported = ["variable_registry.public.concrete.csv", "exports/public_registry.json"]
    lines = [
        f"registry_version: {registry_version}",
        f"export_schema_version: {export_schema_version}",
        f"release_date: '{date.today().isoformat()}'",
        "source_file: variable_registry.source.csv",
        f"source_commit: {source_commit}",
        f"release_status: {release_status}",
        f"public_release_ready: {str(public_release_ready).lower()}",
        "generated_files:",
    ]
    for item in generated_files:
        lines.append(f"  - {item}")
    lines.extend(["conditional_public_generated_files:"])
    for item in public_supported:
        lines.append(f"  - {item}")
    lines.extend([
        "validation_flags:",
        "  fail_on_any_public_manual_for_public_release: true",
        "  require_concrete_ids_without_braces: true",
        "  require_pixel_count_semantics_policy: true",
        "  require_public_artifacts_only_when_release_status_public: true",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checksums(path: Path, root: Path, files: List[str]) -> None:
    lines = []
    for rel in files:
        lines.append(f"{sha256(root / rel)}  {rel}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    concrete_path = Path(args.concrete)
    exports_dir = Path(args.exports_dir)
    manifest_path = Path(args.manifest)
    checksums_path = Path(args.checksums)
    root = manifest_path.parent if manifest_path.parent != Path("") else Path(".")

    source_rows = read_csv(source_path)
    if not source_rows:
        raise SystemExit("Source CSV is empty")

    concrete_rows, concrete_fieldnames = expand_source_rows(source_rows)
    write_csv(concrete_path, concrete_rows, concrete_fieldnames)

    exports_dir.mkdir(parents=True, exist_ok=True)
    internal_payload = {
        "metadata": {
            "registry_version": args.registry_version,
            "export_schema_version": args.export_schema_version,
            "release_status": args.release_status,
            "artifact": "internal_registry.json",
        },
        "variables": to_internal_json_rows(concrete_rows),
    }
    write_json(exports_dir / "internal_registry.json", internal_payload)

    miappe_payload = {
        "metadata": {
            "registry_version": args.registry_version,
            "export_schema_version": args.export_schema_version,
            "release_status": args.release_status,
            "artifact": "miappe_variables.json",
        },
        "variables": to_miappe_json_rows(concrete_rows),
    }
    write_json(exports_dir / "miappe_variables.json", miappe_payload)

    brapi_payload = {
        "metadata": {
            "registry_version": args.registry_version,
            "export_schema_version": args.export_schema_version,
            "release_status": args.release_status,
            "artifact": "brapi_observation_variables.json",
        },
        "result": {"data": to_brapi_json_rows(concrete_rows, args.export_schema_version)},
    }
    write_json(exports_dir / "brapi_observation_variables.json", brapi_payload)

    generated_files = [
        str(concrete_path.relative_to(root)),
        str((exports_dir / "internal_registry.json").relative_to(root)),
        str((exports_dir / "miappe_variables.json").relative_to(root)),
        str((exports_dir / "brapi_observation_variables.json").relative_to(root)),
        "reports/validation_report.json",
    ]

    if args.release_status == "public":
        public_rows = public_concrete_rows(concrete_rows)
        public_csv_path = root / "variable_registry.public.concrete.csv"
        public_json_path = exports_dir / "public_registry.json"
        public_csv_rows = to_public_csv_rows(public_rows)
        write_csv(public_csv_path, public_csv_rows, PUBLIC_CSV_COLUMNS)
        write_json(public_json_path, to_public_registry_json(public_rows, args.registry_version, args.export_schema_version))
        generated_files.extend([
            str(public_csv_path.relative_to(root)),
            str(public_json_path.relative_to(root)),
        ])
        if args.strict_public:
            problems = any_manual_in_rows(public_csv_rows)
            if problems:
                raise SystemExit(f"Strict public build blocked by [MANUAL] in public fields: {problems[:10]}")

    source_commit = args.source_commit or f"registry-v{args.registry_version}-{args.release_status}"
    public_release_ready = args.public_release_ready.lower() == "true"
    write_manifest(
        manifest_path,
        registry_version=args.registry_version,
        export_schema_version=args.export_schema_version,
        release_status=args.release_status,
        generated_files=generated_files,
        source_commit=source_commit,
        public_release_ready=public_release_ready,
    )
    checksum_files = [p for p in generated_files if p != "reports/validation_report.json"] + [str(manifest_path.relative_to(root))]
    write_checksums(checksums_path, root, checksum_files)


if __name__ == "__main__":
    main()
