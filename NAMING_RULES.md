# Naming Rules

## Canonical variable IDs

Concrete variables use lowercase dot-separated identifiers except for preserved vendor filter or band tokens such as `F635` or `A570`.

## Template rows

Template rows may use placeholders such as:

- `{light_source}`
- `{filter}`
- `{stat}`
- `{band_nm}`

These placeholders are authoring-layer only and must not appear in concrete public identifiers.

## FC naming

FluorCam ROI summaries use:

- `fluor.{light_source}.{filter}.{roi}.{stat}`
- `fluor.{light_source}.{filter}.{roi}.pixel_count.px`

## VNIR naming

ROI-level spectral summaries use `.vector`, for example:

- `vnir.emission_spectrum.root_350_900.mean.vector`
- `vnir.reflectance_spectrum.peri_root_350_900.std.vector`

Per-pixel spectra use `.matrix`, for example:

- `vnir.pixel_spectra.root_350_900.matrix`

## Public stability

Concrete public identifiers should not be renamed casually. If change is unavoidable, use `record_status`, `deprecated_in_version`, and `replaced_by_variable_id` to preserve traceability.
