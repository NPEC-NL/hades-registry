# Versioning Policy

The registry uses semantic versioning for the governed registry/schema, not for incidental packaging changes.

## 0.1.0 baseline

Version 0.1.0 is the first **frozen draft baseline**. The preceding 0.0.x packages were development snapshots and are not stable interfaces.

From 0.1.0 onward:

- **PATCH**: wording fixes, corrected references, accession backfills, source hints, or other changes that do not change a canonical variable's identity, meaning, unit, data shape, or expansion grammar
- **MINOR**: backward-compatible additions of genuinely new variables or newly supported source outputs that do not reinterpret existing identifiers
- **MAJOR**: incompatible changes to canonical IDs, semantics, units, observation level, data shape, or template expansion rules

The project intends to avoid further structural/logic changes after 0.1.0. If a semantic correction becomes unavoidable, do not silently reuse an existing ID with a different meaning.

## Public identifier promise

A concrete `variableId` included in a formal public release is a stable public identifier. If it must be replaced:

1. keep the old record
2. set its lifecycle status to `deprecated` or `superseded`
3. record `deprecated_in_version`
4. set `replaced_by_variable_id` when a successor exists
5. add the change to `CHANGELOG.md`

Draft identifiers receive the same treatment where practical, but the public-release promise is the strongest compatibility boundary.
