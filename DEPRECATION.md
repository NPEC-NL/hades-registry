# Deprecation Policy

## Core rule

Do not delete released public variables just because they were superseded.

## When a released variable must change

1. keep the old row;
2. set `record_status` to `deprecated` or `superseded`;
3. fill `deprecated_in_version`;
4. fill `replaced_by_variable_id` where a successor exists;
5. explain the change in `CHANGELOG.md`.

## When deletion is acceptable

Deletion is acceptable only for:
- unreleased draft rows
- rows introduced by mistake before public release
- generated files that can be rebuilt from source

## Why this matters

The public concrete registry is intended to support traceable MIAPPE / BrAPI / internal registry exports. Preserving old IDs keeps archived releases and analyses interpretable.
