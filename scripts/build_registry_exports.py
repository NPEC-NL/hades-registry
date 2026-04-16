\
#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, re
from copy import deepcopy
from datetime import date
from pathlib import Path

DEFAULT_REGISTRY_VERSION = "0.0.4"
DEFAULT_EXPORT_SCHEMA_VERSION = "0.0.4"
PUBLIC_RECORD_STATUS_EXCLUDE = {"draft", "internal_only"}
FILTER_SIGNAL = {
    "F483": "coumarin_related_fluorescence",
    "F513": "assay_dependent_mTurquoise2_or_GFP",
    "F520": "GFP",
    "F593": "YFP_like_reporter",
    "F635": "mCherry",
}

PUBLIC_CSV_COLUMNS = [
    "variableId","parent_variable_id","category","subcategory","variableName",
    "unit","unit_accession","value_type","observation_level","scaleName","scaleClass",
    "system_id","acquisition_modality","acquisition_filter","signal_interpretation",
    "roi_canonical","implementation_roi_alias","acquisition_unit","filter_notes",
    "axis_definition","export_shape","traitName","traitAccNumber",
    "traitEntity","traitEntityAccessionNumber","traitCharacteristic",
    "traitCharacteristicAccessionNumber","methodName","methodDesc","methodRef",
    "record_status","introduced_in_version","deprecated_in_version","replaced_by_variable_id"
]

DISPLAY_STAT = {"mean":"mean","sum":"sum","avg":"average","median":"median","min":"minimum","max":"maximum","std":"standard deviation","stddev":"standard deviation"}
ID_STAT = {"mean":"MEAN","sum":"SUM","avg":"AVG","median":"MEDIAN","min":"MIN","max":"MAX","std":"STD","stddev":"STDDEV"}

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="variable_registry.source.csv")
    p.add_argument("--concrete", default="variable_registry.concrete.csv")
    p.add_argument("--exports-dir", default="exports")
    p.add_argument("--manifest", default="release_manifest.yaml")
    p.add_argument("--checksums", default="checksums.sha256")
    p.add_argument("--registry-version", default=DEFAULT_REGISTRY_VERSION)
    p.add_argument("--export-schema-version", default=DEFAULT_EXPORT_SCHEMA_VERSION)
    p.add_argument("--source-commit", default=None)
    p.add_argument("--public-release-ready", default="false", choices=["true","false"])
    p.add_argument("--release-status", default="draft", choices=["draft","release_candidate","public"])
    p.add_argument("--strict-public", action="store_true")
    return p.parse_args()

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def split_values(v):
    seen = []
    for part in str(v or "").split(","):
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return seen

def replace_placeholders(text, axes, human=False):
    out = str(text or "")
    for k, v in axes.items():
        repl = DISPLAY_STAT.get(v, v) if human and k == "stat" else v
        out = out.replace("{" + k + "}", repl)
    return out

def normalize_system_id(template, axes):
    out = replace_placeholders(template, axes, human=False)
    if "stat" in axes:
        token = ID_STAT.get(axes["stat"], axes["stat"].upper())
        out = re.sub(r"(?<![A-Z0-9])STAT(?![A-Z0-9])", token, out)
        out = re.sub(r"_STAT\b", "_" + token, out)
        out = re.sub(r":STAT\b", ":" + token, out)
    return out

def infer_export_shape(row):
    explicit = str(row.get("export_shape", "")).strip()
    if explicit:
        return explicit
    vt = str(row.get("value_type", "")).strip()
    vid = str(row.get("variableId", "")).strip()
    if vt.startswith("matrix") or vid.endswith(".matrix"):
        return "matrix"
    if vt.startswith("array") or vid.endswith(".vector") or vid.endswith(".series"):
        return "vector"
    return "scalar"

def apply_effective_metadata(row):
    filt = str(row.get("acquisition_filter", "")).strip()
    if filt and "{" not in filt and not str(row.get("signal_interpretation", "")).strip():
        row["signal_interpretation"] = FILTER_SIGNAL.get(filt, "")
    if not str(row.get("export_shape", "")).strip():
        row["export_shape"] = infer_export_shape(row)

def expand_source_rows(source_rows):
    fieldnames = list(source_rows[0].keys()) + ["template_variable_id","expanded_axes_json","source_row_number"]
    concrete = []
    for idx, row in enumerate(source_rows, start=2):
        is_template = row.get("registry_layer") == "authoring_template"
        rule = str(row.get("materialization_rule","") or "")
        stats = split_values(row.get("pattern_stat_values"))
        filters = split_values(row.get("pattern_filter_values"))
        lights = split_values(row.get("pattern_light_source_values"))
        bands = split_values(row.get("pattern_band_values"))

        if is_template:
            if rule == "expand_light_source_x_filter_x_stat":
                axes_iter = [dict(light_source=l, filter=f, stat=s) for l, f, s in itertools.product(lights, filters, stats)]
            elif rule == "expand_light_source_x_filter":
                axes_iter = [dict(light_source=l, filter=f) for l, f in itertools.product(lights, filters)]
            elif rule == "expand_band_x_stat":
                axes_iter = [dict(band_nm=b, stat=s) for b, s in itertools.product(bands, stats)]
            elif rule == "expand_filter_x_stat":
                axes_iter = [dict(filter=f, stat=s) for f, s in itertools.product(filters, stats)]
            elif rule == "expand_filter":
                axes_iter = [dict(filter=f) for f in filters]
            elif rule == "expand_stat":
                axes_iter = [dict(stat=s) for s in stats]
            elif rule == "matrix_no_expand":
                axes_iter = [dict()]
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
                    else:
                        new[col] = replace_placeholders(new.get(col, ""), axes, human=True)
                new["variableId"] = replace_placeholders(row["variableId"], axes, human=False)
                new["registry_layer"] = "canonical_concrete"
                new["materialization_rule"] = "concrete_only"
                apply_effective_metadata(new)
                concrete.append(new)
        else:
            new = deepcopy(row)
            new["template_variable_id"] = ""
            new["expanded_axes_json"] = "{}"
            new["source_row_number"] = str(idx)
            new["registry_layer"] = "canonical_concrete"
            new["materialization_rule"] = "concrete_only"
            apply_effective_metadata(new)
            concrete.append(new)
    return concrete, fieldnames

def clean_text(value):
    text = str(value or "").strip()
    return text or None

def to_internal_json_rows(rows):
    out = []
    for r in rows:
        item = {}
        for k, v in r.items():
            if k == "expanded_axes_json":
                item["expanded_axes"] = json.loads(v or "{}")
            else:
                item[k] = v
        out.append(item)
    return out

def public_rows(rows):
    return [deepcopy(r) for r in rows if r.get("record_status") not in PUBLIC_RECORD_STATUS_EXCLUDE]

def to_public_csv_rows(rows):
    return [{c: r.get(c, "") for c in PUBLIC_CSV_COLUMNS} for r in rows]

def common_payload(r):
    return {
        "variableId": r["variableId"],
        "variableName": r["variableName"],
        "observationLevel": r.get("observation_level",""),
        "traitName": clean_text(r.get("traitName")),
        "traitAccNumber": clean_text(r.get("traitAccNumber")),
        "traitEntity": clean_text(r.get("traitEntity")),
        "traitEntityAccessionNumber": clean_text(r.get("traitEntityAccessionNumber")),
        "traitCharacteristic": clean_text(r.get("traitCharacteristic")),
        "traitCharacteristicAccessionNumber": clean_text(r.get("traitCharacteristicAccessionNumber")),
        "methodName": clean_text(r.get("methodName")),
        "methodDescription": clean_text(r.get("methodDesc")),
        "methodReference": clean_text(r.get("methodRef")),
        "scaleName": clean_text(r.get("scaleName")),
        "scaleClass": clean_text(r.get("scaleClass")),
        "unit": r.get("unit", ""),
        "unitAccession": clean_text(r.get("unit_accession")),
        "systemId": r.get("system_id", ""),
        "category": r.get("category", ""),
        "subcategory": r.get("subcategory", ""),
        "roiCanonical": clean_text(r.get("roi_canonical")),
        "implementationRoiAlias": clean_text(r.get("implementation_roi_alias")),
        "signalInterpretation": clean_text(r.get("signal_interpretation")),
        "filterNotes": clean_text(r.get("filter_notes")),
        "acquisition": {
            "modality": clean_text(r.get("acquisition_modality")),
            "filter": clean_text(r.get("acquisition_filter")),
            "unit": clean_text(r.get("acquisition_unit")),
        },
        "dataShape": {
            "exportShape": clean_text(r.get("export_shape")),
            "axisDefinition": clean_text(r.get("axis_definition")),
        },
        "status": {
            "recordStatus": r.get("record_status",""),
            "introducedInVersion": r.get("introduced_in_version",""),
            "deprecatedInVersion": clean_text(r.get("deprecated_in_version")),
            "replacedByVariableId": clean_text(r.get("replaced_by_variable_id")),
        },
        "notes": clean_text(r.get("notes")),
    }

def to_miappe(rows):
    return [common_payload(r) for r in rows]

def to_brapi(rows, export_schema_version):
    out = []
    for r in rows:
        base = common_payload(r)
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
                "dataType": r.get("value_type",""),
                "scaleClass": base["scaleClass"],
            },
            "contextOfUse": [r.get("observation_level",""), r.get("category",""), r.get("subcategory","")],
            "ontologyReference": {"ontologyName": "MIAPPE-aligned local registry", "version": export_schema_version},
            "unit": r.get("unit",""),
            "unitDbId": base["unitAccession"],
            "systemId": r.get("system_id",""),
            "roiCanonical": base["roiCanonical"],
            "implementationRoiAlias": base["implementationRoiAlias"],
            "signalInterpretation": base["signalInterpretation"],
            "filterNotes": base["filterNotes"],
            "acquisition": base["acquisition"],
            "dataShape": base["dataShape"],
        })
    return out

def to_public_registry(rows, registry_version, export_schema_version):
    return {
        "metadata": {
            "registry_version": registry_version,
            "export_schema_version": export_schema_version,
            "artifact": "public_registry.json",
            "public_identifier_policy": "Concrete variableId values in this artifact are treated as stable public identifiers only after a public release."
        },
        "variables": [
            {
                "variableId": r["variableId"],
                "variableName": r["variableName"],
                "systemId": r["system_id"],
                "category": r["category"],
                "subcategory": r["subcategory"],
                "observationLevel": r["observation_level"],
                "unit": r["unit"],
                "unitAccession": clean_text(r.get("unit_accession")),
                "valueType": r["value_type"],
                "scale": {"scaleName": clean_text(r.get("scaleName")), "scaleClass": clean_text(r.get("scaleClass"))},
                "trait": {"name": clean_text(r.get("traitName")), "accession": clean_text(r.get("traitAccNumber"))},
                "traitEntity": {"name": clean_text(r.get("traitEntity")), "accession": clean_text(r.get("traitEntityAccessionNumber"))},
                "traitCharacteristic": {"name": clean_text(r.get("traitCharacteristic")), "accession": clean_text(r.get("traitCharacteristicAccessionNumber"))},
                "method": {"name": clean_text(r.get("methodName")), "description": clean_text(r.get("methodDesc")), "reference": clean_text(r.get("methodRef"))},
                "roiCanonical": clean_text(r.get("roi_canonical")),
                "implementationRoiAlias": clean_text(r.get("implementation_roi_alias")),
                "signalInterpretation": clean_text(r.get("signal_interpretation")),
                "filterNotes": clean_text(r.get("filter_notes")),
                "acquisition": {
                    "modality": clean_text(r.get("acquisition_modality")),
                    "filter": clean_text(r.get("acquisition_filter")),
                    "unit": clean_text(r.get("acquisition_unit")),
                },
                "dataShape": {
                    "exportShape": clean_text(r.get("export_shape")),
                    "axisDefinition": clean_text(r.get("axis_definition")),
                },
                "status": {
                    "recordStatus": r["record_status"],
                    "introducedInVersion": r["introduced_in_version"],
                    "deprecatedInVersion": clean_text(r.get("deprecated_in_version")),
                    "replacedByVariableId": clean_text(r.get("replaced_by_variable_id")),
                },
            } for r in rows
        ],
    }

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def write_manifest(path, registry_version, export_schema_version, release_status, generated_files, source_commit, public_release_ready):
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
        "  - variable_registry.public.concrete.csv",
        "  - exports/public_registry.json",
        "validation_flags:",
        "  require_concrete_ids_without_braces: true",
        "  require_public_artifacts_only_when_release_status_public: true",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_checksums(path, root, files):
    lines = [f"{sha256(root / rel)}  {rel}" for rel in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    args = parse_args()
    root = Path(".")
    source_path = Path(args.source)
    concrete_path = Path(args.concrete)
    exports_dir = Path(args.exports_dir)
    manifest_path = Path(args.manifest)
    checksums_path = Path(args.checksums)

    source_rows = read_csv(source_path)
    concrete_rows, concrete_fields = expand_source_rows(source_rows)
    write_csv(concrete_path, concrete_rows, concrete_fields)

    exports_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "registry_version": args.registry_version,
        "export_schema_version": args.export_schema_version,
        "release_status": args.release_status,
        "source_commit": args.source_commit or f"registry-v{args.registry_version}-{args.release_status}",
        "public_release_ready": args.public_release_ready == "true",
    }
    write_json(exports_dir / "internal_registry.json", {"metadata": meta | {"artifact":"internal_registry.json"}, "variables": to_internal_json_rows(concrete_rows)})
    write_json(exports_dir / "miappe_variables.json", {"metadata": meta | {"artifact":"miappe_variables.json"}, "variables": to_miappe(concrete_rows)})
    write_json(exports_dir / "brapi_observation_variables.json", {"metadata": meta | {"artifact":"brapi_observation_variables.json"}, "variables": to_brapi(concrete_rows, args.export_schema_version)})

    generated_files = [
        str(concrete_path),
        "exports/internal_registry.json",
        "exports/miappe_variables.json",
        "exports/brapi_observation_variables.json",
        str(manifest_path),
        str(checksums_path),
    ]

    if args.release_status == "public":
        public_list = public_rows(concrete_rows)
        write_csv(root / "variable_registry.public.concrete.csv", to_public_csv_rows(public_list), PUBLIC_CSV_COLUMNS)
        write_json(exports_dir / "public_registry.json", to_public_registry(public_list, args.registry_version, args.export_schema_version))
        generated_files.extend(["variable_registry.public.concrete.csv", "exports/public_registry.json"])
    else:
        for p in [root / "variable_registry.public.concrete.csv", exports_dir / "public_registry.json"]:
            if p.exists():
                p.unlink()

    write_manifest(manifest_path, args.registry_version, args.export_schema_version, args.release_status, generated_files, args.source_commit or f"registry-v{args.registry_version}-{args.release_status}", args.public_release_ready == "true")
    write_checksums(checksums_path, root, generated_files)

if __name__ == "__main__":
    main()
