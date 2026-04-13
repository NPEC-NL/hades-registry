# CHANGELOG

## 0.0.1 - governed public-release draft baseline - 2026-04-13

This release establishes the first governed public-draft baseline of the HADES variable registry.

### Added
- Introduced the HADES-scoped governed source registry as the authoritative hand-edited CSV.
- Added generated concrete and JSON export artifacts.
- Added validation, build, checksum, and release helper scripts.
- Added governance documentation for versioning, naming, deprecation, manual review, and public release policy.

### Changed
- Reset repository versioning to `0.0.1` as the beginning of the governed public-draft line.
- Refactored the source schema toward MIAPPE-style canonical observed-variable fields.
- Removed redundant source fields such as duplicated ontology blocks, `label`, `methodAccNumber`, and redundant hand-maintained scale duplication.
- Kept `scaleName` and `scaleClass` sparse in the source CSV, with generated artifacts allowed to materialize fallback values.
- Removed `export_requirement` and based public selection on lifecycle status instead.

### Status
- `release_status = draft`
- `public_release_ready = false`
- strict public release is intentionally not yet allowed
