PYTHON ?= python3
RELEASE_STATUS ?= public
REGISTRY_VERSION ?= 1.0.0
EXPORT_SCHEMA_VERSION ?= 1.0.0

SOURCE_CSV := variable_registry.source.csv
CONCRETE_CSV := variable_registry.concrete.csv
PUBLIC_CONCRETE_CSV := variable_registry.public.concrete.csv
EXPORTS_DIR := exports
PUBLIC_JSON := $(EXPORTS_DIR)/public_registry.json
REPORT_PATH := reports/validation_report.json
MANIFEST_PATH := release_manifest.yaml
CHECKSUMS_PATH := checksums.sha256
SOURCE_COMMIT ?= registry-v$(REGISTRY_VERSION)
PUBLIC_RELEASE_READY ?= true

.PHONY: build validate validate-public checksum diff-clean release clean-public

build:
	$(PYTHON) scripts/build_registry_exports.py \
	  --source $(SOURCE_CSV) \
	  --concrete $(CONCRETE_CSV) \
	  --public-concrete $(PUBLIC_CONCRETE_CSV) \
	  --exports-dir $(EXPORTS_DIR) \
	  --public-json $(PUBLIC_JSON) \
	  --manifest $(MANIFEST_PATH) \
	  --checksums $(CHECKSUMS_PATH) \
	  --registry-version $(REGISTRY_VERSION) \
	  --export-schema-version $(EXPORT_SCHEMA_VERSION) \
	  --release-status $(RELEASE_STATUS) \
	  --source-commit $(SOURCE_COMMIT) \
	  --public-release-ready $(PUBLIC_RELEASE_READY) \
	  $(if $(filter public,$(RELEASE_STATUS)),--strict-public,)

validate:
	$(PYTHON) scripts/validate_registry.py \
	  --source $(SOURCE_CSV) \
	  --concrete $(CONCRETE_CSV) \
	  --public-concrete $(PUBLIC_CONCRETE_CSV) \
	  --public-json $(PUBLIC_JSON) \
	  --manifest $(MANIFEST_PATH) \
	  --report $(REPORT_PATH) \
	  --release-status $(RELEASE_STATUS)

# Strict public validation is deliberately isolated in a temporary directory.
# It does not rewrite the draft working tree even when the strict build fails.
validate-public:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/exports" "$$tmpdir/reports"; \
	$(PYTHON) scripts/build_registry_exports.py \
	  --source $(SOURCE_CSV) \
	  --concrete "$$tmpdir/variable_registry.concrete.csv" \
	  --public-concrete "$$tmpdir/variable_registry.public.concrete.csv" \
	  --exports-dir "$$tmpdir/exports" \
	  --public-json "$$tmpdir/exports/public_registry.json" \
	  --manifest "$$tmpdir/release_manifest.yaml" \
	  --checksums "$$tmpdir/checksums.sha256" \
	  --registry-version $(REGISTRY_VERSION) \
	  --export-schema-version $(EXPORT_SCHEMA_VERSION) \
	  --release-status public \
	  --source-commit registry-v$(REGISTRY_VERSION) \
	  --public-release-ready true \
	  --strict-public; \
	$(PYTHON) scripts/validate_registry.py \
	  --source $(SOURCE_CSV) \
	  --concrete "$$tmpdir/variable_registry.concrete.csv" \
	  --public-concrete "$$tmpdir/variable_registry.public.concrete.csv" \
	  --public-json "$$tmpdir/exports/public_registry.json" \
	  --manifest "$$tmpdir/release_manifest.yaml" \
	  --report "$$tmpdir/reports/validation_report.json" \
	  --release-status public

checksum:
	@cat $(CHECKSUMS_PATH)

# Rebuild into a temporary tree and compare every normal generated artifact.
# The build uses the same logical source_commit so metadata is deterministic.
diff-clean:
	@tmpdir="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	mkdir -p "$$tmpdir/exports"; \
	$(PYTHON) scripts/build_registry_exports.py \
	  --source $(SOURCE_CSV) \
	  --concrete "$$tmpdir/variable_registry.concrete.csv" \
	  --public-concrete "$$tmpdir/variable_registry.public.concrete.csv" \
	  --exports-dir "$$tmpdir/exports" \
	  --public-json "$$tmpdir/exports/public_registry.json" \
	  --manifest "$$tmpdir/release_manifest.yaml" \
	  --checksums "$$tmpdir/checksums.sha256" \
	  --registry-version $(REGISTRY_VERSION) \
	  --export-schema-version $(EXPORT_SCHEMA_VERSION) \
	  --release-status $(RELEASE_STATUS) \
	  --source-commit $(SOURCE_COMMIT) \
	  --public-release-ready $(PUBLIC_RELEASE_READY) \
	  $(if $(filter public,$(RELEASE_STATUS)),--strict-public,) >/dev/null; \
	diff -u $(CONCRETE_CSV) "$$tmpdir/variable_registry.concrete.csv"; \
	diff -u $(EXPORTS_DIR)/internal_registry.json "$$tmpdir/exports/internal_registry.json"; \
	diff -u $(EXPORTS_DIR)/miappe_variables.json "$$tmpdir/exports/miappe_variables.json"; \
	diff -u $(EXPORTS_DIR)/brapi_observation_variables.json "$$tmpdir/exports/brapi_observation_variables.json"; \
	diff -u $(MANIFEST_PATH) "$$tmpdir/release_manifest.yaml"; \
	diff -u $(CHECKSUMS_PATH) "$$tmpdir/checksums.sha256"; \
	if [ "$(RELEASE_STATUS)" = "public" ]; then \
	  diff -u $(PUBLIC_CONCRETE_CSV) "$$tmpdir/variable_registry.public.concrete.csv"; \
	  diff -u $(PUBLIC_JSON) "$$tmpdir/exports/public_registry.json"; \
	fi

release:
	bash scripts/release_registry.sh

clean-public:
	rm -f $(PUBLIC_CONCRETE_CSV) $(PUBLIC_JSON)
