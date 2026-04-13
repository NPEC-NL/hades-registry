# HADES Variable Registry

Governed, platform-specific variable registry for the HADES phenotyping system.

## Scope

This repository contains the governed variable registry for the HADES platform.

HADES is a platform-specific phenotyping system for sterile, plate-based seedling experiments with automated handling, multichannel fluorescence imaging, VNIR hyperspectral imaging, and root-focused analysis workflows. The registry in this repository is therefore **HADES-scoped**: it describes variables emitted, derived, or curated for the current HADES implementation and its associated data products.

The repository is intended to support:

- stable variable definition for HADES-generated measurements and analysis outputs
- machine-readable export to downstream formats used in project data management and publication support
- transparent governance of naming, versioning, validation, and release mechanics
- traceable linkage between authoring-layer registry definitions and concrete exported variables

This repository is **not** intended to serve as a universal plant phenotyping ontology or a cross-platform NPEC registry. Where possible, variables are aligned to existing ontology terms and MIAPPE-compatible concepts, but the registry remains centered on the realities of the HADES workflow, including platform-specific ROIs, imaging outputs, and implementation-defined emitted variables.

Two registry layers are maintained:

- **authoring-layer source definitions**, including grouped template rows used for maintainability
- **canonical concrete variables**, generated from the source layer for stable downstream use

As a result, this repository should be understood as a governed, platform-specific registry that supports HADES data interpretation, export, and publication, rather than as a final public registry service or a platform-neutral standard.

## Future multi-platform note

This repository is intentionally scoped to HADES.

Other NPEC platforms may share selected measurement families, vendor export structures, or high-level concepts with HADES, but that does not imply that their variables should be merged into this repository. In particular, platforms with different observation units, biological scope, imaging geometry, segmentation logic, or experimental context may require independent registries even when some outputs appear superficially similar.

If future cross-platform harmonization is pursued, the preferred approach is expected to be:

1. maintain separate platform-specific registries
2. reuse shared governance conventions where appropriate
3. connect comparable concepts through explicit crosswalks or harmonized mappings rather than by collapsing distinct platform variables into a single flat registry

Accordingly, any future multi-platform integration should be treated as a separate harmonization effort, not as an assumption built into the current HADES registry.

## Authoritative source and generated artifacts

### Authoritative source

- `variable_registry.source.csv`
  - the only CSV that should be edited by hand
  - may contain both `authoring_template` rows and `canonical_concrete` rows
  - may contain governance fields, pattern metadata, and `[MANUAL]` placeholders

### Generated artifacts

- `variable_registry.concrete.csv`
- `exports/internal_registry.json`
- `exports/miappe_variables.json`
- `exports/brapi_observation_variables.json`
- `release_manifest.yaml`
- `checksums.sha256`
- `reports/validation_report.json`

If `RELEASE_STATUS=public`, the build also generates:

- `variable_registry.public.concrete.csv`
- `exports/public_registry.json`

Do not hand-edit generated files.

## Relationship to MIAPPE and BrAPI

This repository is **not itself** a MIAPPE standard release, a BrAPI server, or a public ontology distribution. Instead, it uses the governed HADES source CSV as an authoring layer and generates export artifacts that act as a **pragmatic bridge** to MIAPPE-compatible and BrAPI-compatible structures.

### MIAPPE alignment

MIAPPE defines an observed variable as the description of how a measurement has been made, typically combining a trait or measured characteristic with a method and a scale. In this repository, MIAPPE-style columns in the source CSV support that form of representation for HADES outputs, and `exports/miappe_variables.json` is generated from those columns as a derived bridge artifact.

### BrAPI alignment

BrAPI phenotyping models include concepts such as Observation Variables, Traits, Methods, and Scales. The generated `exports/brapi_observation_variables.json` is intended as a bridge from the HADES registry into a structure that can be consumed by BrAPI-oriented tooling or later transformed into BrAPI service payloads.

### Status of MIAPPE / BrAPI exports in this repository

The MIAPPE and BrAPI artifacts in this repository are:

- **derived exports** from the governed HADES CSV
- **compatibility-oriented bridge artifacts** for data exchange and publication support
- **not yet a fully standardized public ontology release**
- **not a substitute for future curation, harmonization, or endpoint-specific implementation work**

## Current draft state

Current repository state:

- `registry_version = 0.0.1`
- `export_schema_version = 0.0.1`
- `release_status = draft`
- `public_release_ready = false`

This version is the **starting governed public-release draft baseline** for the HADES registry.

## Source schema principles

The source CSV is designed for **maintainability first**.

### Canonical observed-variable mapping fields

The source schema uses MIAPPE-style canonical mapping fields such as:

- `variableId`
- `variableName`
- `traitName`
- `traitAccNumber`
- `traitMappingConfidence`
- `traitEntity`
- `traitEntityAccessionNumber`
- `traitCharacteristic`
- `traitCharacteristicAccessionNumber`
- `methodName`
- `methodDesc`
- `methodRef`
- `scaleName`
- `scaleClass`

Older duplicated mapping blocks are intentionally not maintained in parallel.

### Method fields

- `methodName` should stay short and stable
- `methodDesc` carries implementation-specific detail, including HADES / PSI / vendor context when needed
- `methodRef` may be used for external method documentation when available

### Unit versus scale

The source CSV keeps both unit-oriented and scale-oriented concepts, but they are not stored in the same way.

#### Data-side representation

These fields describe the emitted or computed values as they exist in HADES outputs:

- `unit`
- `unit_accession`
- `value_type`
- `observation_level`

#### Observed-variable-side representation

These fields support MIAPPE / Crop Ontology style interpretation:

- `scaleName`
- `scaleClass`

To reduce manual duplication in the hand-edited source CSV:

- leave `scaleName` blank when it adds no information beyond `unit`
- leave `scaleClass` blank when it can be inferred safely from context
- generated artifacts may materialize fallback scale values from `unit`, `value_type`, and related context

So the source CSV is intentionally sparse where the scale would otherwise just repeat the unit.

## Public versus source-only fields

Not every field in the source CSV is intended for public release.

### Source-only / governance-oriented fields

These may exist in the source CSV for maintainability, validation, and release management, but are normally excluded from public-facing artifacts:

- `registry_layer`
- `materialization_rule`
- `manual_class`
- `traitMappingConfidence`
- pattern bookkeeping fields such as `is_pattern`, `pattern_stat_values`, and `pattern_band_values`
- source-only curation / validation helpers

### Public-facing fields

Public-facing artifacts should retain only the concrete semantics needed to identify, interpret, and reuse the variable in downstream systems. Exact inclusion rules are defined by `PUBLIC_RELEASE_POLICY.md` and enforced by validation.

## Canonical identifiers and stability promise

Concrete exported `variableId` values are treated as the canonical identifiers of this registry once they are released publicly.

This repository therefore follows these rules:

- grouped template identifiers are authoring-only and are not public identifiers
- concrete identifiers must not contain unresolved template braces
- public concrete identifiers should be treated as stable
- if a released concrete identifier must change, the previous identifier should be preserved and marked through deprecation or supersession rather than silently removed
- deprecation and replacement should be traceable through lifecycle fields in the source CSV

See `DEPRECATION.md`, `VERSIONING.md`, and `NAMING_RULES.md` for detailed policy.

## Release states

The repository supports multiple release states.

Typical draft or internal work may still contain:

- `[MANUAL]` placeholders in the source layer
- optional unresolved mappings
- source-only governance fields
- non-public export artifacts intended for review

A strict public release is more constrained and requires:

- `RELEASE_STATUS=public`
- `public_release_ready: true` in the manifest
- generation of `variable_registry.public.concrete.csv`
- generation of `exports/public_registry.json`
- successful public-release validation with no disallowed unresolved public-facing placeholders

## Build and validation workflow

Only the source CSV should be edited directly.

Typical maintainer workflow:

1. edit `variable_registry.source.csv`
2. run validation
3. regenerate concrete and export artifacts
4. confirm the repository is diff-clean
5. update manifest and changelog as needed

### Common commands

```bash
make build
make validate
make checksum
make diff-clean
```

Strict public-release validation is intentionally separate:

```bash
make validate-public
```

`make validate-public` runs in an isolated temporary directory so a failing public check does not dirty the working tree.

## Meaning of `[MANUAL]`

`[MANUAL]` is an explicit placeholder indicating that a field still needs human review or curation.

Typical reasons include:

- ontology review
- method mapping review
- ROI controlled-vocabulary review
- unit policy review

`[MANUAL]` may be acceptable in the authoring-layer source CSV, depending on policy, but should be blocked or sanitized appropriately in downstream exports according to `MANUAL_REVIEW.md` and `PUBLIC_RELEASE_POLICY.md`.

## Why template rows exist

Some variable families in HADES are repetitive and differ only along well-defined axes such as statistic (`mean`, `sum`, `std`) or wavelength-band values. To keep authoring maintainable, the source CSV may therefore contain grouped template rows.

These template rows are allowed only in the authoring layer. They must be expanded into concrete variable definitions before stable downstream use and before any strict public export.

## References

Official MIAPPE resources:

- https://www.miappe.org/
- https://www.miappe.org/overview/

Official BrAPI resources:

- https://brapi.org/
- https://brapi.org/specification

These references are included for context because the repository exports are designed as compatibility bridges to MIAPPE-style and BrAPI-style structures, not because this repository replaces those standards.
