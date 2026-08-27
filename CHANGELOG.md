# Changelog

## 0.1.0 - frozen draft baseline

This is the first version intended to serve as a stable draft interface for the HADES variable registry. Earlier 0.0.x packages were schema-development snapshots.

### Canonical model finalized

- removed fluorescence `{light_source}` expansion; FC canonical IDs are now `fluor.{filter}.{roi}.{stat}`
- retained the complete programmable excitation recipe as acquisition metadata because a FluorCam protocol may combine several light channels at independent percentages
- resolved FC1/FC2 availability from the concrete emission filter during generation rather than encoding the unit in the ID
- separated fluorescence intensity from channel-independent ROI-mask pixel counts
- added exclusive `peri_root` and inclusive `root_plus_peri` mask/intensity families
- retained implementation aliases such as `dilated_root_exclusive` and `dilated_root` without using `dilated` in canonical IDs

### VNIR model finalized

- renamed VNIR1 white-light variables from reflectance to **transmittance**
- documented VNIR1 processing with matched dark and white references
- retained VNIR2 as UV-induced **fluorescence emission** acquired in reflection geometry
- made VNIR2 per-pixel spectral artifacts explicitly emission-specific
- retained the full exported spectral axis at approximately 349.9nm-899.1nm; manuscript-specific narrower windows remain downstream analysis choices

### Root/ROI method alignment

- root architecture methods now describe U-Net segmentation, skeleton/graph conversion, and Dijkstra primary-root path reconstruction
- root path length and mask-area pixel counts are represented as distinct variables
- standardized root method reference to the actual image-analysis preprint DOI

### Boxeed source alignment

- restricted the Boxeed canonical raw-output family to the seven fields present in the source table: Seed Side, Length, SSE, AxesAngle, Width, Surface, and PixelCount
- removed downstream calculated descriptors such as L/S ratio and roundness from the raw-output registry
- preserved vendor uncertainty where the exact image-processing formulas are not disclosed

### Governance and build

- froze registry and export schema versions at 0.1.0
- reset all `introduced_in_version` values to 0.1.0 for the first stable draft baseline
- updated validation for the frozen schema and family order
- fixed temporary public validation so it cannot modify draft working-tree artifacts
- made checksum generation deterministic and removed checksum self-hashing
- documented the source-only edit SOP: `make build`, `make validate`, `make diff-clean`
