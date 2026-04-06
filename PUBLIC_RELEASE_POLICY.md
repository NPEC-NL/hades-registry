# Public Release Policy

This document defines what changes when `RELEASE_STATUS=public`.

## 1. Public artifacts generated only for public release

If and only if `RELEASE_STATUS=public`, the build must generate:
- `variable_registry.public.concrete.csv`
- `exports/public_registry.json`

These artifacts are the public-facing concrete registry layer.

## 2. Public field policy

### Source-only / internal governance fields
These fields must stay out of public CSV and public JSON:
- `registry_layer`
- `materialization_rule`
- `measurement_method`
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
- `export_requirement`
- `template_variable_id`
- `expanded_axes_json`
- `source_row_number`

Rationale: these are authoring, curation, or implementation-support fields rather than stable public semantics.

### Public CSV fields
`variable_registry.public.concrete.csv` keeps only the concrete, curation-stable columns needed for public exchange:
- `variable_id`
- `parent_variable_id`
- `label`
- `category`
- `subcategory`
- `reported_name`
- `unit`
- `value_type`
- `observation_level`
- `system_id`
- `trait`
- `trait_accession`
- `trait_entity`
- `trait_entity_accession`
- `trait_characteristic`
- `trait_characteristic_accession`
- `method`
- `method_accession`
- `scale`
- `scale_accession`
- `roi_class`
- `roi_class_accession`
- `variable_role`
- `record_status`
- `introduced_in_version`
- `deprecated_in_version`
- `replaced_by_variable_id`

### Public JSON fields
`exports/public_registry.json` is intentionally slimmer than the internal registry. It contains:
- artifact metadata
- stable `variable_id`
- human-facing label / reported name
- system, category, and observation metadata
- MIAPPE-aligned trait decomposition
- ROI context where relevant
- variable role
- lifecycle / deprecation status

It does not contain source-only authoring metadata or `[MANUAL]` placeholders.

## 3. `[MANUAL]` policy for public release

For draft and release-candidate builds:
- `[MANUAL]` is allowed in the source CSV
- public-preview validation is allowed to fail
- internal and MIAPPE/BrAPI draft exports may still be built

For `RELEASE_STATUS=public`:
- `[MANUAL]` must not appear in any public CSV field
- `[MANUAL]` must not appear in `public_registry.json`
- public release validation must fail otherwise

This is intentionally stricter than the draft policy.

## 4. Canonical public identifier freeze promise

Once a concrete `variable_id` appears in a public release artifact, it is treated as a stable public identifier.

### Promise
Maintainers should not rename or repurpose released public concrete IDs casually.

### If change is unavoidable
Do not silently overwrite semantics.
Instead:
1. keep the old identifier in the source registry;
2. set `record_status` to `deprecated` or `superseded`;
3. fill `deprecated_in_version`;
4. fill `replaced_by_variable_id` when there is a successor;
5. document the reason in `CHANGELOG.md`.

## 5. Public release validation requirements

A public release must fail if any of the following are true:
- public artifact files are missing
- duplicate public concrete IDs exist
- braces remain in public concrete IDs
- source-only fields leak into public CSV
- `[MANUAL]` appears anywhere in a public artifact
- public artifact ID sets disagree with the public subset of the concrete registry
- a `superseded` row has no replacement
- a `deprecated` or `superseded` row has no `deprecated_in_version`

## 6. HADES-scoped promise

This public freeze promise is about the already released HADES concrete IDs.
It does not prevent future cross-platform harmonization.
It does mean that future Helios or non-PSI convergence should be handled by:
- harmonized exports
- platform-specific source registries
- deprecation / supersession where truly necessary

rather than by casually renaming published HADES identifiers.
