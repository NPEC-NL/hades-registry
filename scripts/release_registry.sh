#!/usr/bin/env bash
set -euo pipefail
make build
make validate
make diff-clean
make validate-public
make checksum
printf '%s\n' 'Registry 1.0.0 public artifacts rebuilt and validated.'
