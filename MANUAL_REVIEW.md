# Manual Review Policy

## Purpose

`[MANUAL]` marks fields that still need curator review.

## Allowed locations

`[MANUAL]` is allowed in the source CSV.

It must not appear in a strict public release artifact.

## Current manual review classes

- `ontology_review`
- `method_mapping`
- `roi_cv`
- `unit_policy`

`manual_class` may contain multiple values joined by `|`.

## Draft vs public behavior

### Draft / release candidate
- source may contain `[MANUAL]`
- public-preview validation may fail
- internal and exchange draft artifacts may still be generated

### Public
- no `[MANUAL]` may remain in any public artifact
- strict public validation must pass

## Responsibility model

Recommended review ownership:
- ontology accessions: ontology curator / data steward
- method accessions: assay domain maintainer
- ROI CV accessions: image-analysis maintainer plus ontology curator
- unit / scale policy: registry maintainer
