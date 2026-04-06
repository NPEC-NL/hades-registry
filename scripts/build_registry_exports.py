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

DEFAULT_REGISTRY_VERSION = "1.2.1"
DEFAULT_EXPORT_SCHEMA_VERSION = "1.1.0"
PUBLIC_RELEASE_VALUES = {"required_for_public_export", "optional_for_public_export"}

PUBLIC_CSV_COLUMNS = [
    "variable_id",
    "parent_variable_id",
    "label",
    "category",
    "subcategory",
    "reported_name",
    "unit",
    "value_type",
    "observation_level",
    "system_id",
    "trait",
    "trait_accession",
    "trait_entity",
    "trait_entity_accession",
    "trait_characteristic",
    "trait_characteristic_accession",
    "method",
    "method_accession",
    "scale",
    "scale_accession",
    "roi_class",
    "roi_class_accession",
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
    "measurement_method",
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
    "export_requirement",
    "template_variable_id",
    "expanded_axes_json",
    "source_row_number",
}

MIAPPE_OPTIONAL_NULLABLE = {
    "trait_accession",
    "trait_entity_accession",
    "trait_characteristic_accession",
    "method_accession",
    "scale_accession",
    "roi_class",
    "roi_class_accession",
    "notes",
    "qc_recommended",
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
    parser.add_argument(
        "--release-status",
        default="draft",
        choices=["draft", "release_candidate", "public"],
    )
    parser.add_argument(
        "--strict-public",
        action="store_true",
        help="When release-status=public, fail if any public artifact field would still contain [MANUAL].",
    )
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
    if value is None:
        return []
    text = str(value).strip()
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
        out = out.replace("{stat}", token)
        out = re.sub(r"(?<![A-Z0-9])STAT(?![A-Z0-9])", token, out)
        out = re.sub(r"_STAT\b", f"_{token}", out)
        out = re.sub(r":STAT\b", f":{token}", out)
    if "band_nm" in axes and "A{band_nm}" not in template:
        out = out.replace("BAND", f"BAND_A{axes['band_nm']}", 1)
    return out


def strip_template_notes(notes: str, template_variable_id: str, axes: Dict[str, str]) -> str:
    text = notes or ""
    text = re.sub(r"Pattern row\.[^.]*\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Pattern variable\.[^.]*\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Authoring-layer template row; expand to concrete variable IDs before MIAPPE/BrAPI export\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Use fully expanded variable_id in JSON/BrAPI/MIAPPE exports\.?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    provenance = f"Expanded from template {template_variable_id} with axes {json.dumps(axes, sort_keys=True)}."
    return (text + " " + provenance).strip() if text else provenance


def expand_source_rows(source_rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[str]]:
    fieldnames = list(source_rows[0].keys()) + ["template_variable_id", "expanded_axes_json", "source_row_number"]
    concrete: List[Dict[str, str]] = []
    for idx, row in enumerate(source_rows, start=2):
        is_pattern = (row.get("registry_layer") == "authoring_template") or (row.get("is_pattern", "").strip().lower() == "yes")
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
                new["template_variable_id"] = row["variable_id"]
                new["expanded_axes_json"] = json.dumps(axes, sort_keys=True)
                new["source_row_number"] = str(idx)
                for col in list(new.keys()):
                    if col == "system_id":
                        new[col] = normalize_system_id(new.get(col, ""), axes)
                    elif col == "notes":
                        new[col] = strip_template_notes(new.get(col, ""), row["variable_id"], axes)
                    else:
                        new[col] = replace_placeholders(new.get(col, ""), axes, human=True)
                new["variable_id"] = replace_placeholders(row["variable_id"], axes, human=False)
                new["registry_layer"] = "canonical_concrete"
                new["materialization_rule"] = "concrete_only"
                new["is_pattern"] = "no"
                new["pattern_band_values"] = ""
                new["pattern_stat_values"] = ""
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
            concrete.append(new)
    concrete.sort(key=lambda r: r["variable_id"])
    return concrete, fieldnames


def sanitize_export_text(value: str | None) -> str | None:
    text = str(value or "").replace("[MANUAL]", " ").strip()
    text = re.sub(r"\s+", " ", text).strip(" ;,")
    if not text:
        return None
    return text


def clean_optional(value: str | None) -> str | None:
    text = sanitize_export_text(value)
    if text is None:
        return None
    return text


def manual_free(value: str | None) -> bool:
    return "[MANUAL]" not in str(value or "")


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
    rows = [deepcopy(r) for r in concrete_rows if r.get("export_requirement") in PUBLIC_RELEASE_VALUES and r.get("record_status") != "draft"]
    rows.sort(key=lambda r: r["variable_id"])
    return rows


def to_public_csv_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    public_rows: List[Dict[str, str]] = []
    for row in rows:
        public_rows.append({col: row.get(col, "") for col in PUBLIC_CSV_COLUMNS})
    return public_rows


def to_miappe_json_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        item = {
            "observation_variable_id": row["variable_id"],
            "observation_variable_name": row["label"],
            "reported_name": row["reported_name"],
            "observation_level": row["observation_level"],
            "trait": clean_optional(row.get("trait")),
            "trait_accession": clean_optional(row.get("trait_accession")),
            "trait_entity": clean_optional(row.get("trait_entity")),
            "trait_entity_accession": clean_optional(row.get("trait_entity_accession")),
            "trait_characteristic": clean_optional(row.get("trait_characteristic")),
            "trait_characteristic_accession": clean_optional(row.get("trait_characteristic_accession")),
            "method": clean_optional(row.get("method")),
            "method_accession": clean_optional(row.get("method_accession")),
            "scale": clean_optional(row.get("scale")),
            "scale_accession": clean_optional(row.get("scale_accession")),
            "value_type": row["value_type"],
            "unit": row["unit"],
            "variable_role": row["variable_role"],
            "category": row["category"],
            "subcategory": row["subcategory"],
            "roi": {
                "class": clean_optional(row.get("roi_class")),
                "class_accession": clean_optional(row.get("roi_class_accession")),
            },
            "status": {
                "record_status": row["record_status"],
                "introduced_in_version": row["introduced_in_version"],
                "deprecated_in_version": clean_optional(row.get("deprecated_in_version")),
                "replaced_by_variable_id": clean_optional(row.get("replaced_by_variable_id")),
            },
            "notes": clean_optional(row.get("notes")),
            "qc_recommended": clean_optional(row.get("qc_recommended")),
        }
        out.append(item)
    return out


def to_brapi_json_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    data: List[Dict[str, object]] = []
    for row in rows:
        data.append(
            {
                "observationVariableDbId": row["variable_id"],
                "observationVariableName": row["label"],
                "trait": {
                    "traitName": clean_optional(row.get("trait")),
                    "traitDbId": clean_optional(row.get("trait_accession")),
                    "entity": clean_optional(row.get("trait_entity")),
                    "entityDbId": clean_optional(row.get("trait_entity_accession")),
                    "attribute": clean_optional(row.get("trait_characteristic")),
                    "attributeDbId": clean_optional(row.get("trait_characteristic_accession")),
                },
                "method": {
                    "methodName": clean_optional(row.get("method")),
                    "methodDbId": clean_optional(row.get("method_accession")),
                },
                "scale": {
                    "scaleName": clean_optional(row.get("scale")),
                    "scaleDbId": clean_optional(row.get("scale_accession")),
                    "dataType": row["value_type"],
                    "validValues": None,
                },
                "contextOfUse": [row["observation_level"], row["category"], row["subcategory"]],
                "ontologyReference": {
                    "documentationLinks": [],
                    "ontologyName": "MIAPPE-aligned local registry",
                    "version": DEFAULT_EXPORT_SCHEMA_VERSION,
                },
                "unit": row["unit"],
                "systemId": row["system_id"],
                "variableRole": row["variable_role"],
            }
        )
    return data


def to_public_registry_json(rows: List[Dict[str, str]], registry_version: str, export_schema_version: str) -> Dict[str, object]:
    return {
        "metadata": {
            "registry_version": registry_version,
            "export_schema_version": export_schema_version,
            "artifact": "public_registry.json",
            "public_identifier_policy": "Concrete variable_id values in this artifact are treated as stable public identifiers.",
        },
        "variables": [
            {
                "variable_id": row["variable_id"],
                "label": row["label"],
                "reported_name": row["reported_name"],
                "system_id": row["system_id"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "observation_level": row["observation_level"],
                "unit": row["unit"],
                "value_type": row["value_type"],
                "trait": {
                    "name": clean_optional(row.get("trait")),
                    "accession": clean_optional(row.get("trait_accession")),
                },
                "trait_entity": {
                    "name": clean_optional(row.get("trait_entity")),
                    "accession": clean_optional(row.get("trait_entity_accession")),
                },
                "trait_characteristic": {
                    "name": clean_optional(row.get("trait_characteristic")),
                    "accession": clean_optional(row.get("trait_characteristic_accession")),
                },
                "method": {
                    "name": clean_optional(row.get("method")),
                    "accession": clean_optional(row.get("method_accession")),
                },
                "scale": {
                    "name": clean_optional(row.get("scale")),
                    "accession": clean_optional(row.get("scale_accession")),
                },
                "roi": {
                    "class": clean_optional(row.get("roi_class")),
                    "accession": clean_optional(row.get("roi_class_accession")),
                },
                "variable_role": row["variable_role"],
                "status": {
                    "record_status": row["record_status"],
                    "introduced_in_version": row["introduced_in_version"],
                    "deprecated_in_version": clean_optional(row.get("deprecated_in_version")),
                    "replaced_by_variable_id": clean_optional(row.get("replaced_by_variable_id")),
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
                problems.append((row.get("variable_id", ""), key))
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
    lines.extend([
        "conditional_public_generated_files:",
    ])
    for item in public_supported:
        lines.append(f"  - {item}")
    lines.extend([
        "validation_flags:",
        "  fail_on_required_manual_for_draft_exports: false",
        "  fail_on_any_public_manual_for_public_release: true",
        "  require_concrete_ids_without_braces: true",
        "  require_pixel_count_semantics_policy: true",
        "  require_public_artifacts_only_when_release_status_public: true",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checksums(path: Path, root: Path, files: List[str]) -> None:
    lines = []
    for rel in files:
        rel_path = root / rel
        lines.append(f"{sha256(rel_path)}  {rel}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)
    concrete_path = Path(args.concrete)
    exports_dir = Path(args.exports_dir)
    manifest_path = Path(args.manifest)
    checksums_path = Path(args.checksums)

    source_rows = read_csv(source_path)
    if not source_rows:
        raise SystemExit("Source CSV is empty")

    concrete_rows, concrete_fieldnames = expand_source_rows(source_rows)
    write_csv(concrete_path, concrete_rows, concrete_fieldnames)

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

    public_rows = public_concrete_rows(concrete_rows)
    miappe_payload = {
        "metadata": {
            "registry_version": args.registry_version,
            "export_schema_version": args.export_schema_version,
            "release_status": args.release_status,
            "artifact": "miappe_variables.json",
        },
        "variables": to_miappe_json_rows(public_rows),
    }
    write_json(exports_dir / "miappe_variables.json", miappe_payload)

    brapi_payload = {
        "metadata": {
            "registry_version": args.registry_version,
            "export_schema_version": args.export_schema_version,
            "release_status": args.release_status,
            "artifact": "brapi_observation_variables.json",
        },
        "result": {
            "data": to_brapi_json_rows(public_rows),
        },
    }
    write_json(exports_dir / "brapi_observation_variables.json", brapi_payload)

    generated_files = [
        concrete_path.name,
        f"{exports_dir.name}/internal_registry.json",
        f"{exports_dir.name}/miappe_variables.json",
        f"{exports_dir.name}/brapi_observation_variables.json",
    ]

    if args.release_status == "public":
        public_manual = any_manual_in_rows(public_rows)
        if args.strict_public and public_manual:
            first = ", ".join(f"{vid}:{field}" for vid, field in public_manual[:10])
            raise SystemExit(f"Public release blocked because [MANUAL] remains in public rows: {first}")
        public_csv_path = concrete_path.with_name("variable_registry.public.concrete.csv")
        public_csv_rows = to_public_csv_rows(public_rows)
        write_csv(public_csv_path, public_csv_rows, PUBLIC_CSV_COLUMNS)
        public_json_path = exports_dir / "public_registry.json"
        write_json(public_json_path, to_public_registry_json(public_rows, args.registry_version, args.export_schema_version))
        generated_files.extend([public_csv_path.name, f"{exports_dir.name}/public_registry.json"])
    else:
        for path in [concrete_path.with_name("variable_registry.public.concrete.csv"), exports_dir / "public_registry.json"]:
            if path.exists():
                path.unlink()

    source_commit = args.source_commit or f"registry-v{args.registry_version}-{args.release_status}"
    public_release_ready = args.public_release_ready.lower() == "true"

    write_manifest(
        manifest_path,
        registry_version=args.registry_version,
        export_schema_version=args.export_schema_version,
        release_status=args.release_status,
        generated_files=generated_files + ["reports/validation_report.json", checksums_path.name],
        source_commit=source_commit,
        public_release_ready=public_release_ready,
    )
    write_checksums(checksums_path, manifest_path.parent, generated_files)


if __name__ == "__main__":
    main()
