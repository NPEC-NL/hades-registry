# Public Release Policy

Version **1.0.0** is the first public, release-ready HADES variable-registry version.

The normal 1.0.0 release state is:

- `release_status: public`
- `public_release_ready: true`
- `variable_registry.public.concrete.csv` present
- `exports/public_registry.json` present

A formal public build requires both `RELEASE_STATUS=public` and `PUBLIC_RELEASE_READY=true` and must pass `make validate`, `make diff-clean`, and `make validate-public`.

Public artifacts omit authoring-only pattern/governance fields and contain only concrete variable identifiers. Once a concrete identifier is included in a public release, it is stable and can only be replaced through the deprecation/supersession policy.
