#!/usr/bin/env bash
set -euo pipefail
make build
make validate
make diff-clean
make checksum
printf '%s\n' 'Registry artifacts rebuilt and validated.'
