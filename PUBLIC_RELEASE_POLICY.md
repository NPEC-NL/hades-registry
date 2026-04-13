# Public Release Policy

This document defines what changes when `RELEASE_STATUS=public`.

## 1. Public artifacts generated only for public release

If and only if `RELEASE_STATUS=public`, the build must generate:
- `variable_registry.public.concrete.csv`
- `exports/public_registry.json`

These artifacts are the public-facing concrete registry layer.

## 2. Public field policy

### Source-only / internal governance fields
These fields stay out of public artifacts:
- `registry_layer`
- `materialization_rule`
- `source_table_hint`
- `qc_recommended`
- `component`
- `core_nm`
- `in_bundle`
- `is_pattern`
- `pattern_band_values`
- `pattern_stat_values`
- `stat_axis_semantics`
- `manual_class`
- `template_variable_id`
- `expanded_axes_json`
- `source_row_number`
- `traitMappingConfidence`

### Public CSV fields
`variable_registry.public.concrete.csv` keeps the concrete, release-facing semantics needed for interpretation and reuse:
- `variableId`
- `parent_variable_id`
- `category`
- `subcategory`
- `variableName`
- `unit`
- `unit_accession`
- `value_type`
- `observation_level`
- `scaleName`
- `scaleClass`
- `system_id`
- `roi_class`
- `traitName`
- `traitAccNumber`
- `traitEntity`
- `traitEntityAccessionNumber`
- `traitCharacteristic`
- `traitCharacteristicAccessionNumber`
- `methodName`
- `methodDesc`
- `methodRef`
- `variable_role`
- `record_status`
- `introduced_in_version`
- `deprecated_in_version`
- `replaced_by_variable_id`

### Public row selection
Without a separate export-requirement flag, the public subset is defined by concrete rows whose `record_status` is not `draft` and not `internal_only`.

## 3. `[MANUAL]` policy for public release

For draft builds:
- `[MANUAL]` is allowed in the source CSV
- internal and bridge exports may still be generated

For `RELEASE_STATUS=public`:
- `[MANUAL]` must not appear in any public artifact field
- public release validation must fail otherwise

## 4. Canonical public identifier freeze promise

Once a concrete `variableId` appears in a public release artifact, it is treated as a stable public identifier.

If change is unavoidable:
1. keep the old identifier in the source registry;
2. set `record_status` to `deprecated` or `superseded`;
3. fill `deprecated_in_version`;
4. fill `replaced_by_variable_id` when there is a successor;
5. document the reason in `CHANGELOG.md`.

## 5. HADES scope

This release policy applies to HADES-scoped concrete identifiers.
Future cross-platform harmonization should use explicit crosswalks, harmonized exports, or separate platform registries rather than casually renaming released HADES identifiers.
