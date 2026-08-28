# Curation Review Policy

The source registry is curated by maintainers before a public release is published.

Review should focus on:

- whether a variable is actually emitted by the referenced HADES, vendor, or analysis workflow
- whether units, value type, observation level, and data shape agree with the source output
- whether ontology accessions are exact, approximate, or intentionally absent
- whether method descriptions describe the implemented computation rather than an inferred biological interpretation
- whether ROI names clearly distinguish biological concepts from implementation aliases
- whether template expansion reflects real finite axes and does not manufacture impossible acquisition combinations

Unknown ontology accessions may be left empty. Do not invent accessions merely to fill a field.

The validator checks structural consistency, but domain review remains necessary before each public release.
