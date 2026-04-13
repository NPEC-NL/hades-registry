#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${SOURCE_CSV:-$ROOT/variable_registry.source.csv}"
CONCRETE="${CONCRETE_CSV:-$ROOT/variable_registry.concrete.csv}"
EXPORTS_DIR="${EXPORTS_DIR:-$ROOT/exports}"
MANIFEST="${MANIFEST_PATH:-$ROOT/release_manifest.yaml}"
CHECKSUMS="${CHECKSUMS_PATH:-$ROOT/checksums.sha256}"
REPORT="${REPORT_PATH:-$ROOT/reports/validation_report.json}"
REGISTRY_VERSION="${REGISTRY_VERSION:-0.0.1}"
EXPORT_SCHEMA_VERSION="${EXPORT_SCHEMA_VERSION:-0.0.1}"
RELEASE_STATUS="${RELEASE_STATUS:-draft}"
SOURCE_COMMIT="${SOURCE_COMMIT:-registry-v${REGISTRY_VERSION}-${RELEASE_STATUS}}"
PUBLIC_RELEASE_READY="${PUBLIC_RELEASE_READY:-false}"

extra_args=()
if [ "$RELEASE_STATUS" = "public" ]; then
  extra_args+=(--strict-public)
fi

python3 "$ROOT/scripts/build_registry_exports.py"   --source "$SOURCE"   --concrete "$CONCRETE"   --exports-dir "$EXPORTS_DIR"   --manifest "$MANIFEST"   --checksums "$CHECKSUMS"   --registry-version "$REGISTRY_VERSION"   --export-schema-version "$EXPORT_SCHEMA_VERSION"   --release-status "$RELEASE_STATUS"   --source-commit "$SOURCE_COMMIT"   --public-release-ready "$PUBLIC_RELEASE_READY"   "${extra_args[@]}"

python3 "$ROOT/scripts/validate_registry.py"   --source "$SOURCE"   --concrete "$CONCRETE"   --public-concrete "$ROOT/variable_registry.public.concrete.csv"   --public-json "$EXPORTS_DIR/public_registry.json"   --manifest "$MANIFEST"   --report "$REPORT"   --release-status "$RELEASE_STATUS"
