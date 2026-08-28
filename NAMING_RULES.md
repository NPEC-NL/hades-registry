# Naming Rules

## Canonical identifier

`variableId` is the unique registry identifier. Concrete IDs are dot-separated and must contain no braces.

`system_id` may identify a HADES/pipeline/vendor source family and is not required to be unique. Never substitute `system_id` for `variableId` as a database primary key.

## Authoring placeholders

The 1.0.0 source grammar permits:

- `{filter}` for RootCam/FluorCam emission filters
- `{stat}` for a finite summary-statistic axis
- `{band_nm}` for PSI vendor band columns

Excitation light is **not** a placeholder axis because one FluorCam protocol can combine several excitation channels at arbitrary percentages.

## Root and ROI mask variables

Use graph/path terminology for one-dimensional root-axis measurements, for example:

- `root.primary.length.px`
- `root.lateral.total_length.px`

Use channel-independent ROI mask variables for segmentation area represented as pixel count:

- `roi.main_root.pixel_count.px`
- `roi.peri_root.pixel_count.px`
- `roi.root_plus_peri.pixel_count.px`

`peri_root` means the exclusive dilation zone. `root_plus_peri` means the inclusive dilated root mask.

## Fluorescence

Source template:

`fluor.{filter}.{roi}.{stat}`

Examples after expansion:

- `fluor.F483.main_root.mean`
- `fluor.F635.main_root.sum`
- `fluor.F513.node.mean`

Do not encode FC1/FC2, biological reporter names, or the excitation recipe in the canonical ID.

## VNIR

White-light transmittance:

- `vnir.transmittance_spectrum.root_350_900.mean.vector`
- `vnir.transmittance_spectrum.peri_root_350_900.std.vector`

UV-induced fluorescence emission:

- `vnir.emission_spectrum.root_350_900.mean.vector`
- `vnir.emission_spectrum.peri_root_350_900.sum.vector`

Per-pixel VNIR2 fluorescence spectra:

- `vnir.emission_pixel_spectra.root_350_900.matrix`
- `vnir.emission_pixel_spectra.peri_root_350_900.matrix`

Use `.vector` for one spectrum per ROI and `.matrix` for a variable-cardinality collection of pixel spectra with spatial coordinates. `.matrix` describes logical shape, not file extension; HADES 1.0.0 stores large per-pixel matrix exports as Parquet by default, with CSV optional.

## PSI vendor patterns

Vendor table axes may remain authoring templates, for example:

`psi.vnir.band.A{band_nm}.{stat}`

The generator materializes concrete registry IDs while preserving the vendor family identity in `system_id`.

## Stability

1.0.0 is the first public naming baseline. Concrete identifiers distributed in this release are stable; replacement requires deprecation/supersession metadata.
