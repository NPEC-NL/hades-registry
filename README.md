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

## Future multi-platform note

This repository is intentionally scoped to HADES. Other NPEC platforms may share selected measurement families, vendor export structures, or high-level concepts with HADES, but that does not imply that their variables should be merged into this repository. If future cross-platform harmonization is pursued, the preferred approach is to keep separate platform-specific registries and connect comparable concepts through explicit crosswalks or harmonized mappings.

## Authoritative source and generated artifacts

### Authoritative source

- `variable_registry.source.csv`
  - the only CSV that should be edited by hand
  - may contain both `authoring_template` rows and `canonical_concrete` rows
  - may contain governance fields, pattern metadata, and internal notes needed for generation

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

This repository is **not itself** a MIAPPE standard release, a BrAPI server, or a public ontology distribution. Instead, it uses the governed HADES source CSV as an authoring layer and generates export artifacts that act as a pragmatic bridge to MIAPPE-compatible and BrAPI-compatible structures.

## Current draft state

Current repository state:

- `registry_version = 0.0.4`
- `export_schema_version = 0.0.4`
- `release_status = draft`
- `public_release_ready = false`

## Source schema principles

The source CSV is designed for maintainability first.

### Canonical mapping fields

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

### FC normalization model

HADES FluorCam / RootCam fluorescence variables are modeled as filter- and light-source-aware ROI summaries:

- canonical template pattern: `fluor.{light_source}.{filter}.{roi}.{stat}`
- pixel-count rows remain separate and do not expand over `stat`
- biological interpretation such as mCherry, coumarin-related fluorescence, mTurquoise2, or GFP remains metadata in `signal_interpretation` and `filter_notes`

This reflects the actual analysis logic: the pipeline aligns archived fluorescence images using filter-specific geometry and then extracts the same ROI summaries regardless of downstream assay interpretation.

### VNIR normalization model

HADES VNIR variables are split into:

- **emission / fluorescence spectra** acquired under UV excitation
- **reflectance spectra** acquired under white-light illumination

ROI-level VNIR summaries are modeled as `.vector` variables and are not scalar-expanded over wavelength. Per-pixel VNIR spectra are represented as matrix-like outputs rather than ordinary scalar variables.

### ROI naming

The registry currently keeps `peri_root` as the canonical ROI while preserving implementation aliases such as `dilated_root_exclusive` or `dilation_zone_exclusive` in metadata. This is intentional during the current draft stage.

### Source row order

The source CSV row order is meaningful and should be preserved during manual editing. The current maintained family order is:

1. root
2. FC / fluorescence
3. VNIR
4. PSI vendor exports
5. seed / Boxeed

## Validation and build

### Validate

```bash
make validate
```

### Build artifacts

```bash
make build
```

### Strict public-release gate

```bash
make validate-public
```

### Diff-clean check

```bash
make diff-clean
```

`make validate-public` runs in a temporary directory so failed strict-public validation does not dirty the working tree.

## References

- MIAPPE: https://www.miappe.org/
- BrAPI: https://brapi.org/
- Crop Ontology: https://cropontology.org/
