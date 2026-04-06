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


## What this repository contains

This repository maintains one authoritative hand-edited source file and multiple generated artifacts.

### Authoritative source

- `variable_registry.source.csv`
  - the only CSV that should be edited by hand
  - may contain both `authoring_template` rows and `canonical_concrete` rows
  - may contain governance fields, pattern metadata, and `[MANUAL]` placeholders

### Generated registry artifacts

- `variable_registry.concrete.csv`
  - generated from the source CSV
  - contains only concrete rows intended for stable downstream use
- `exports/internal_registry.json`
  - internal JSON representation generated from the source layer
- `exports/miappe_variables.json`
  - generated bridge export structured for MIAPPE-oriented observed-variable use
- `exports/brapi_observation_variables.json`
  - generated bridge export structured for BrAPI-oriented observation-variable use
- `variable_registry.public.concrete.csv`
  - generated only for a strict public release
- `exports/public_registry.json`
  - generated only for a strict public release

### Governance and release files

- `release_manifest.yaml`
- `CHANGELOG.md`
- `VERSIONING.md`
- `NAMING_RULES.md`
- `MANUAL_REVIEW.md`
- `DEPRECATION.md`
- `PUBLIC_RELEASE_POLICY.md`
- `reports/validation_report.json`

## Relationship to MIAPPE and BrAPI

This repository is **not itself** a MIAPPE standard release, a BrAPI server, or a public ontology distribution. Instead, it uses the governed HADES source CSV as an authoring layer and generates export artifacts that act as a **pragmatic bridge** to MIAPPE-compatible and BrAPI-compatible structures.

### MIAPPE alignment

MIAPPE defines an **observed variable** as the description of how a measurement has been made, typically combining a trait or measured characteristic with a method and a scale. MIAPPE also allows multiple variables that otherwise share trait, method, and scale to be distinguished by plant part or similar context when needed. In this repository, the MIAPPE-oriented fields in the source CSV and the generated `exports/miappe_variables.json` are intended to support that style of representation for HADES outputs.

Practically, this means:

- the source CSV stores HADES-specific variables and mappings
- MIAPPE-related columns in the source layer are used to structure those variables into a MIAPPE-compatible observed-variable form
- the generated MIAPPE JSON is a derived export, not the authoritative source
- unresolved placeholders may exist in the source layer, but should be cleaned or blocked according to export policy before any strict public release

### BrAPI alignment

BrAPI phenotyping models include concepts such as **Observation Variables**, **Traits**, **Methods**, and **Scales**. The generated `exports/brapi_observation_variables.json` is intended as a bridge from the HADES registry into a structure that can be consumed by BrAPI-oriented tooling or later transformed into BrAPI service payloads.

Practically, this means:

- BrAPI exports are generated from the governed source CSV rather than edited directly
- the BrAPI JSON in this repository is an export artifact, not a claim that the registry is already a complete public BrAPI implementation
- the export emphasizes stable concrete identifiers and machine-readable decomposition of variable meaning

### Status of MIAPPE/BrAPI exports in this repository

The MIAPPE and BrAPI artifacts in this repository should be understood as:

- **derived exports** from the governed HADES CSV
- **compatibility-oriented bridge artifacts** for data exchange and publication support
- **not yet a fully standardized public ontology release**
- **not a substitute for future curation, harmonization, or endpoint-specific implementation work**

This is intentional. The goal of the repository is to provide a traceable and governed source of truth for HADES variables while making downstream MIAPPE-compatible and BrAPI-compatible outputs feasible and reproducible.

## Public versus internal fields

Not every field in the source CSV is intended for public release.

### Source-only or internal governance fields

These fields may appear in the source CSV for maintainability, validation, and release management, but are normally excluded from public-facing exports:

- `registry_layer`
- `manual_class`
- `export_requirement`
- pattern bookkeeping fields such as `is_pattern`, `pattern_stat_values`, `pattern_band_values`, and `materialization_rule`
- internal notes intended only for maintainers or release logic

### Public-facing fields

Public-facing exports should retain only the fields needed to identify, interpret, and reuse the variable in downstream systems. Exact inclusion rules are defined by `PUBLIC_RELEASE_POLICY.md` and enforced by validation.

## Canonical identifiers and stability promise

Concrete exported `variable_id` values are treated as the canonical identifiers of this registry once they are released publicly.

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
- internal-only governance fields
- non-public export artifacts intended for review

A strict public release is more constrained and may require:

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
make validate
make build
make checksum
make diff-clean
```

Strict public-release validation is intentionally separate:

```bash
make validate-public
```

Public validation should run in an isolated temporary working directory so failed public checks do not dirty the normal working tree.

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

## Why this registry is HADES-specific

HADES combines a workflow that includes sterile plate preparation, Boxeed-based seed handling, RootCam / FluorCam imaging, VNIR hyperspectral imaging, and platform-specific downstream analysis. Even when another platform shares a sensor family or vendor export type, differences in observation unit, segmentation logic, ROI semantics, experimental context, and emitted outputs can still make the variables meaningfully different.

For that reason, this repository does not assume that apparently similar variables from other platforms belong in the same governed registry.

## Future multi-platform note

This repository is intentionally scoped to HADES.

Other NPEC platforms may share selected measurement families, vendor export structures, or high-level concepts with HADES, but that does not imply that their variables should be merged into this repository. In particular, platforms with different observation units, biological scope, imaging geometry, segmentation logic, or experimental context may require independent registries even when some outputs appear superficially similar.

If future cross-platform harmonization is pursued, the preferred approach is expected to be:

1. maintain separate platform-specific registries
2. reuse shared governance conventions where appropriate
3. connect comparable concepts through explicit crosswalks or harmonized mappings rather than by collapsing distinct platform variables into a single flat registry

Accordingly, any future multi-platform integration should be treated as a separate harmonization effort, not as an assumption built into the current HADES registry.

## External standards referenced

Official MIAPPE resources:

- https://www.miappe.org/
- https://www.miappe.org/overview/

Official BrAPI resources:

- https://brapi.org/
- https://brapi.org/specification

These references are included for context because the repository exports are designed as compatibility bridges to MIAPPE-style and BrAPI-style structures, not because this repository replaces those standards.
