#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-/tmp/agriscope_backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "${BACKUP_DIR}"

echo "[AgriScope] Starting database backup to ${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-agriscope_user}" "${POSTGRES_DB:-agriscope}" | gzip > "${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
echo "[AgriScope] Backup complete: ${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"
