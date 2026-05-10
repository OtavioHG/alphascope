#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-artifacts/backups}"
DB_PATH="${2:-data/alphascope.db}"
mkdir -p "${BACKUP_DIR}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

if [[ -f "${DB_PATH}" ]]; then
  cp "${DB_PATH}" "${BACKUP_DIR}/$(basename "${DB_PATH%.*}")_${TIMESTAMP}.${DB_PATH##*.}"
  echo "Database backup created from ${DB_PATH} into ${BACKUP_DIR}"
else
  echo "Database not found at ${DB_PATH}" >&2
  exit 1
fi
