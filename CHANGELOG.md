# CHANGELOG

## 1.2.1 - public-ready governance draft - 2026-04-06

### Added
- Added `PUBLIC_RELEASE_POLICY.md`.
- Added conditional public-release artifacts:
  - `variable_registry.public.concrete.csv`
  - `exports/public_registry.json`
- Added strict public-release validation rules.
- Added repository automation:
  - root `Makefile`
  - `.github/workflows/validate-registry.yml`
- Added generated-artifact diff-clean checks.

### Changed
- Kept the package in `draft` status but made the structure ready for a future strict public release.
- Tightened the public-release rule so that any remaining public-facing `[MANUAL]` placeholder blocks `RELEASE_STATUS=public`.
- Clarified which columns are source-only, internal-only, and public-exportable.
- Made the canonical public identifier freeze promise explicit.

### Not changed
- No scientific variable semantics were changed.
- No existing HADES canonical IDs were renamed.
- No public release was cut in this version.

## 1.2.0 - governed draft release - 2026-04-06

### Added
- Introduced `variable_registry.source.csv` as the authoritative hand-edited source file.
- Added lifecycle and governance columns.
- Added generated concrete and JSON exports.
- Added validation and build scripts.
- Added release helper script, manifest, checksum file, and governance documentation.
