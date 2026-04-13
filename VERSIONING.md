# Versioning Policy

This repository starts its governed public-draft history at **0.0.1**.

The earlier working numbers used during pre-governance iterations are not part of the public draft version history and should not be treated as externally meaningful release identifiers.

## Registry version

`registry_version` applies to the meaning and governance state of the authoritative registry.

### PATCH
Use for:
- wording fixes
- accession backfills
- note clarifications
- documentation-only updates
- automation, manifest, checksum, or validation refinements that do not change variable semantics

### MINOR
Use for:
- backward-compatible addition of new variables
- new template families
- new ROI / band / stat combinations under current naming rules
- new governed fields that do not rename released concrete IDs

### MAJOR
Use for:
- renamed released concrete IDs
- changed variable semantics
- changed units or value types
- changed expansion rules that alter already released concrete IDs

## Export schema version

`export_schema_version` applies to the shape of generated artifacts.

Changing JSON field names, nesting, or public CSV structure is an export schema change.
Changing only registry content while keeping generated artifact structure stable is a registry content change.

## Stability rule

Released concrete public `variableId` values are stable identifiers.
If a mistake is found:
1. prefer deprecation and replacement;
2. avoid deletion after public release;
3. record the change in `CHANGELOG.md`;
4. fill `replaced_by_variable_id` where a successor exists.
