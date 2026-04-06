# Versioning Policy

The registry and its generated exports follow semantic versioning.

## Registry version

`registry_version` applies to the meaning and governance state of the authoritative registry.

### PATCH
Use for:
- wording fixes
- typo fixes
- accession backfills
- note clarifications
- documentation-only updates
- public-field-policy clarifications
- automation, manifest, checksum, or validation refinements that do not change variable semantics

### MINOR
Use for:
- backward-compatible addition of new variables
- new template families
- new ROI / band / stat combinations under current naming rules
- public-release artifact additions that do not rename released concrete IDs
- new optional governance fields

### MAJOR
Use for:
- renamed released concrete IDs
- changed variable semantics
- changed units or value types
- changed expansion rules that alter already released concrete IDs
- changed public identifier policy

## Export schema version

`export_schema_version` applies to the structure of generated JSON outputs.

- changing JSON field names or nesting = schema version change
- adding a new public artifact format = schema version change
- changing only registry content while keeping the JSON shape stable = registry version change

## Stability rule

Released concrete public IDs are stable identifiers.
If a mistake is found:
1. prefer deprecation and replacement;
2. avoid deletion;
3. record the change in `CHANGELOG.md`;
4. fill `replaced_by_variable_id` where a successor exists.
