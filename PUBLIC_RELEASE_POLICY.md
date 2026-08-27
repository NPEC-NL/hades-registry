# Public Release Policy

The repository is structurally capable of producing public artifacts, but version 0.1.0 is currently a **frozen draft**, not a public release.

Normal draft state:

- `release_status: draft`
- `public_release_ready: false`
- no `variable_registry.public.concrete.csv`
- no `exports/public_registry.json`

A formal public build requires both:

- `RELEASE_STATUS=public`
- `PUBLIC_RELEASE_READY=true`

Public artifacts omit authoring-only pattern/governance fields and contain only concrete variable identifiers. A public build must pass `make validate-public` before release.

Once a concrete identifier is included in a public release, it is treated as stable and can only be replaced through the deprecation/supersession policy.
