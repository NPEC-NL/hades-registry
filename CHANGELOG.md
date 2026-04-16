# Changelog

## 0.0.4 - draft

Small patch release after manual audit.

### Source-table fixes

- added `{light_source}` to FluorCam `parent_variable_id` and `system_id`
- normalized UTF-8 / escaped text forms such as `Seed shape - SSE`, `Seed shape - L/S ratio`, `array<float>`, `matrix<float>`, `349.9nm-899.1nm`, and `&gt;=`
- set `core_nm`, `in_bundle`, and `is_pattern` explicitly for `vnir.reflectance` rows
- set all `psi.vnir` rows to `acquisition_modality = psi_vendor_vnir`
- simplified `psi.vnir` trait entities to `plant` with `PO:0000003`
- updated `seed.length_area_ratio` to use `ratio (shape elongation)` with `PATO:0001470`
- shortened FluorCam filter notes
- removed `artifact_class`
- removed remaining manual placeholders and the `manual_class` column

### Generator / export changes

- removed artifact-class handling from generated exports
- removed manual-placeholder-specific validation logic
- regenerated concrete and bridge export artifacts under version `0.0.4`
