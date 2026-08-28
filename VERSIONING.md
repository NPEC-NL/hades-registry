# Versioning Policy

The registry uses semantic versioning for the governed registry/schema, not for incidental packaging changes.

## 1.0.0 public baseline

Version **1.0.0** is the first public release and the compatibility baseline for canonical HADES variable identifiers. Earlier `0.x` versions were pre-release development/frozen-draft snapshots.

From 1.0.0 onward:

- **PATCH**: wording fixes, corrected references, accession backfills, source hints, or other changes that do not change a canonical variable's identity, meaning, unit, data shape, or expansion grammar
- **MINOR**: backward-compatible additions of genuinely new variables or newly supported source outputs that do not reinterpret existing identifiers
- **MAJOR**: incompatible changes to canonical IDs, semantics, units, observation level, data shape, or template expansion rules

## Public identifier promise

A concrete `variableId` included in 1.0.0 or a later public release is a stable public identifier. If it must be replaced:

1. keep the old record
2. set its lifecycle status to `deprecated` or `superseded`
3. record `deprecated_in_version`
4. set `replaced_by_variable_id` when a successor exists
5. add the change to `CHANGELOG.md`

Do not silently reuse a released identifier with changed semantics.
