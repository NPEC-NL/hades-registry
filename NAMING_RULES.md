# Canonical Naming Rules

## General principles

- Use lowercase dot-separated canonical IDs.
- Keep each axis explicit in the ID.
- Keep the family and measured concept near the front.
- Reserve braces only for authoring-layer template rows.
- Never publish concrete IDs containing braces.

## Concrete variable IDs

Concrete IDs are fully expanded and stable.

Examples:
- `root.primary.length.px`
- `fluor.mCherry.main_root.mean`
- `vnir.emission_peak_wavelength.root_425_600.nm`
- `psi.vnir.band.A570.avg`

## Template variable IDs

Template IDs are allowed only in `variable_registry.source.csv`.

Examples:
- `fluor.mCherry.main_root.{stat}`
- `vnir.emission_spectrum.root_425_600.{stat}`
- `psi.vnir.band.A{band_nm}.{stat}`

## Reserved suffix rules

### Statistic suffixes
Use:
- `.mean`
- `.sum`
- `.std`
- `.avg`
- `.median`
- `.min`
- `.max`

### Scalar unit suffixes
Use:
- `.nm` for wavelength-valued scalars
- `.deg` for angle-valued scalars
- `.px` only where the implementation-level unit really is pixels

### Pixel count rows
Use `.pixel_count.px` for count-of-pixels variables.
These rows must remain semantically consistent:
- `unit = px`
- `quality = count`
- `trait_characteristic = count`
- `scale = count`
- `variable_role = analysis_derived`

### Structured outputs
Use:
- `.vector` for wide-form vectors
- `.series` for ordered protocol/time/frame series

## Public vs authoring-only naming

Public and stable:
- concrete IDs in `variable_registry.public.concrete.csv`
- concrete IDs in `public_registry.json`

Authoring-only:
- brace patterns such as `{stat}` and `{band_nm}`
- template expansion instructions
- template-only bookkeeping metadata

## Platform scope

Current IDs are HADES-scoped.
Future Helios or non-PSI additions should not force a rename of already released HADES public IDs.
