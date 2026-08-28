# Deprecation and Supersession

Do not delete a previously distributed concrete variable merely because a better name or mapping is found.

For a variable that remains interpretable but should no longer be used, set:

- `record_status=deprecated`
- `deprecated_in_version=<version>`
- `replaced_by_variable_id=<successor>` when applicable

For a variable whose role is explicitly taken over by another canonical variable, use `record_status=superseded` and record the successor.

A replacement should normally be a new row. Do not change the old row's identifier and pretend it has always had the new meaning.

Version 1.0.0 is the first public compatibility baseline. Silent ID or semantic rewrites are not allowed after this release; use deprecation or supersession instead.
