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

## Responsibility model

Recommended review ownership:
- ontology accessions: ontology curator / data steward
- method references and method phrasing: assay domain maintainer
- ROI vocabulary: image-analysis maintainer plus ontology curator
- unit and scale policy: registry maintainer
