# HADES Variable Registry

Governed, platform-specific variable registry for the HADES phenotyping system at NPEC.

## Scope

This repository contains the governed variable registry for the HADES platform.

HADES is a platform-specific phenotyping system for sterile, plate-based seedling experiments with automated handling, monochromatic backlit root imaging, programmable multichannel fluorescence imaging, VNIR hyperspectral imaging, and root-focused analysis workflows. The registry is therefore **HADES-scoped**: it describes variables emitted, derived, or curated for the current HADES implementation and its associated data products.

The repository supports:

- stable variable definitions for HADES-generated measurements and analysis outputs
- machine-readable export to downstream formats used in data management and publication
- transparent governance of naming, versioning, validation, and release mechanics
- traceable linkage between maintainable authoring templates and concrete exported variables

This repository is **not** a universal plant phenotyping ontology or a cross-platform NPEC registry. Existing ontology terms and MIAPPE-compatible concepts are reused where they fit, but HADES-specific ROIs, image-processing products, acquisition settings, and vendor exports remain explicit.

## Future multi-platform note

Other NPEC platforms can share sensor families, vendor software, or high-level concepts with HADES without sharing the same variable semantics. For example, another PSI platform can use FluorCam or VNIR hardware while observing a different biological compartment, growth system, or imaging geometry. Cross-platform work should therefore maintain platform-specific registries and connect comparable concepts through explicit crosswalks rather than collapsing distinct platform outputs into one flat registry.

## 1.0.0 status: first public release

Version **1.0.0** is the first public, release-ready version of the HADES variable registry. Earlier `0.x` packages were pre-release development and frozen-draft snapshots and are not part of the public compatibility promise.

Release metadata is:

- `registry_version: 1.0.0`
- `export_schema_version: 1.0.0`
- `release_status: public`
- `public_release_ready: true`

Concrete `variableId` values included in 1.0.0 are treated as stable public identifiers. Later semantic replacements must use the deprecation/supersession mechanism rather than silently changing an existing public identifier.

## Authoritative source and generated artifacts

### Hand-edited source

`variable_registry.source.csv` is the **only registry table edited by hand**.

It can contain:

- `canonical_concrete` rows
- `authoring_template` rows such as `{filter}`, `{stat}`, and `{band_nm}` families
- HADES acquisition metadata
- ontology mappings and method descriptions
- governance/lifecycle fields

### Generated files

Do not hand-edit:

- `variable_registry.concrete.csv`
- `exports/internal_registry.json`
- `exports/miappe_variables.json`
- `exports/brapi_observation_variables.json`
- `release_manifest.yaml`
- `checksums.sha256`
- `reports/validation_report.json`

The 1.0.0 public build additionally emits:

- `variable_registry.public.concrete.csv`
- `exports/public_registry.json`

## Registry layers

`registry_layer=authoring_template` identifies a compact source row that the generator expands. A template may use `{filter}`, `{stat}`, or `{band_nm}`. Public/concrete identifiers never contain braces.

`registry_layer=canonical_concrete` identifies a source row that already represents one concrete variable.

The legacy `is_pattern` column is retained because it reflects source/export provenance in some families, but **template expansion is governed by `registry_layer` and `materialization_rule`**, not by `is_pattern` alone.

## Canonical identifier versus system identifier

`variableId` is the registry's unique canonical identifier.

`system_id` records the closest HADES-, pipeline-, or vendor-native identifier. It is **not required to be globally unique**. For HADES-native FC variables it can carry the concrete emission filter because that dimension is explicitly represented by the processing pipeline. For PSI vendor tables, a `system_id` may instead identify an export family while the concrete vendor column dimension remains in `variableId`.

Downstream applications that require a stable unique key should use `variableId`.

## Root architecture and ROI-mask variables

Backlit RootCam images are segmented by the HADES image-analysis pipeline. Root masks are skeletonized and represented as graphs; the primary-root path is reconstructed on the skeleton with Dijkstra's shortest-path algorithm. This makes `root.primary.length.px` a one-dimensional graph/path measurement expressed in image-native pixel coordinates, not a root-area measurement.

Mask area is represented separately by channel-independent ROI pixel-count variables such as:

- `roi.main_root.pixel_count.px`
- `roi.lateral_root.pixel_count.px`
- `roi.peri_root.pixel_count.px`
- `roi.root_plus_peri.pixel_count.px`

`peri_root` is the exclusive region formed by dilating the root mask and subtracting the original root. `root_plus_peri` is the inclusive dilated region and corresponds to the implementation alias `dilated_root`. These mask sizes are **not duplicated for each fluorescence filter**.

## Fluorescence model

### Canonical IDs are filter-driven

RootCam/FluorCam scalar fluorescence summaries use the source template:

`fluor.{filter}.{roi}.{stat}`

where `{stat}` currently expands to `mean` and `sum`.

The emission filter is part of the canonical variable identity because it defines which acquired image is being quantified. Biological meanings such as mCherry, GFP, mTurquoise2, or coumarin-associated fluorescence are assay context and remain in metadata rather than being hard-coded into `variableId`.

### Excitation is acquisition metadata, not an ID axis

FluorCam acquisition protocols can activate one or several light channels simultaneously and assign each a controller percentage. Protocols stored with the raw acquisition can include `Act1`, `Act2`, `Super`, `FAR`, `UV`, `RBLUE`, `BLUE`, `GREEN`, `AMBER`, and `RED`, together with settings such as `Filter`, `ShutterTime`, and `Sensitivity`.

Because the excitation recipe is a **vector of per-channel settings**, not one categorical light source, there is intentionally no `{light_source}` placeholder in the canonical ID. The source field `acquisition_light_profile` documents where the complete recipe is found. A protocol such as `UV=100` and all other channels `0` is one possible acquisition, not a fixed registry class.

Controller percentages also must not be interpreted as directly comparable physical irradiance values across channels. PSI calibration data are instrument- and channel-specific and provide separate percentage-to-intensity relationships. If calibrated physical excitation is needed for an experiment, it should be reconstructed from the recorded protocol plus the applicable calibration record rather than encoded into the variable ID.

Accordingly, `variableId` identifies the **output variable schema**, not the complete optical assay condition. Observations acquired with different excitation profiles can share the same canonical variable ID, but quantitative comparison requires the associated acquisition protocol/settings to be retained and checked.

### Filter availability and acquisition unit

FC1 and FC2 have overlapping but non-identical filter sets. The source template therefore stores `acquisition_unit=derived_from_filter_capability`; the generator resolves it to `FC1`, `FC2`, or `FC1|FC2` in concrete rows. FC1/FC2 remain implementation metadata, not part of the canonical identifier.
For a shared filter, `FC1|FC2` denotes compatible hardware in the registry definition; the actual unit used for a particular acquisition should still be retained in experiment/acquisition metadata.

## VNIR model

The same VNIR camera supports two different illumination geometries/workflows.

### VNIR1: white-light transmittance

VNIR1 uses broadband cool-white illumination transmitted through the plate toward the camera. The processing path uses both dark and white references and computes relative transmittance as `(raw - dark) / (white - dark)` before denoising and optional ROI extraction.

Canonical ROI spectra use:

- `vnir.transmittance_spectrum.root_350_900.{stat}.vector`
- `vnir.transmittance_spectrum.peri_root_350_900.{stat}.vector`

### VNIR2: UV-induced fluorescence emission

VNIR2 uses 365 nm UV illumination in reflection geometry to excite fluorescence. The measured wavelength-resolved signal is therefore modelled as **fluorescence emission**, not as UV reflectance. The pipeline uses matched dark correction, spectral/spatial denoising, two-stage RootCam-mask registration, and extraction of root/peri-root spectra.

Canonical ROI spectra use:

- `vnir.emission_spectrum.root_350_900.{stat}.vector`
- `vnir.emission_spectrum.peri_root_350_900.{stat}.vector`

Per-pixel VNIR2 spectra plus spatial coordinates are matrix-like artifacts and use:

- `vnir.emission_pixel_spectra.root_350_900.matrix`
- `vnir.emission_pixel_spectra.peri_root_350_900.matrix`

Per-pixel matrix exports are stored as **Parquet by default**; CSV is available as an optional interchange format. NPZ is no longer part of the registry export contract.

The camera's exported spectral axis is approximately **349.9nm-899.1nm**. Narrower ranges such as 425-600 nm are downstream analysis windows used for particular biological questions and are not the canonical raw-output axis.

The current main manuscript uses the VNIR2 fluorescence-emission workflow for its biological hyperspectral analysis, while the hardware/method description also documents the VNIR1 white-light transmittance capability.

## PSI vendor exports

Rows under `psi.*` describe vendor/PlantScreen Data Analyzer products. They are kept separate from HADES custom-analysis variables because their semantics and table structures are defined by the PSI software layer.

For `psi.vnir.*`, the observed entity is `plant` (`PO:0000003`). Patterned vendor columns such as `A{band_nm}-{stat}` remain compact in the source CSV and are expanded to concrete `variableId` values by the generator.

## Boxeed model

The registry intentionally represents the seven raw measurement columns present in the Boxeed seed export:

1. `Seed Side`
2. `Length`
3. `SSE`
4. `AxesAngle`
5. `Width`
6. `Surface`
7. `PixelCount`

These map to the seven `seed.*` source rows in the same order. Each raw row represents one imaged seed side (`Seed Side` 0 or 1). Values such as L/S ratio, roundness, experiment-specific selection thresholds, or averages across the two orientations are downstream calculations and are not separate canonical raw-output variables unless a future source export emits them directly.

The Boxeed vendor does not disclose the exact image-segmentation, ellipse-fit, or calibration algorithms, so the registry does not invent implementation details that are not documented.

## Implementation and research resources

Stable public implementation and technical-resource entry points used by the registry are:

- HADES fluorescence/RootCam analysis: https://github.com/valerian-meline/HADES_FC
- HADES hyperspectral analysis: https://github.com/valerian-meline/HADES_HSI
- HADES research resources: https://npec-nl.github.io/hades-research-resources

The research-resources page is the stable landing page for the HADES method materials while the method manuscript remains under review. Camera technical specifications and FluorCam light-calibration resources can be linked there without changing registry method references.

## MIAPPE and BrAPI bridge exports

The registry's MIAPPE-style fields (`variableName`, trait/entity/characteristic, method, and scale fields) are the canonical authoring representation for observed-variable semantics.

`exports/miappe_variables.json` and `exports/brapi_observation_variables.json` are **generated interoperability bridges**. They do not claim that the HADES registry is itself a public ontology, a fully standardized MIAPPE submission, or a BrAPI server. HADES-specific acquisition and data-shape metadata are retained as local extension fields where useful.

## Source row order

Source row order is deliberate and is preserved by the generator:

1. root architecture / segmentation-mask variables
2. FC fluorescence variables
3. VNIR variables
4. PSI vendor exports
5. Boxeed seed variables

Do not alphabetically sort the source CSV.

## Maintainer SOP

For a normal registry edit:

```bash
# 1. Edit only variable_registry.source.csv
# 2. Regenerate derived artifacts
make build

# 3. Validate the source and generated concrete registry
make validate

# 4. Confirm the checked-in generated artifacts are reproducible
make diff-clean
```

Do not manually patch the concrete CSV, JSON exports, manifest, or checksums.

Use `make validate-public` to run the strict public-release gate in a temporary directory. It must not dirty the normal working tree.

## References

- MIAPPE: https://www.miappe.org/
- BrAPI: https://brapi.org/
- Crop Ontology: https://cropontology.org/
