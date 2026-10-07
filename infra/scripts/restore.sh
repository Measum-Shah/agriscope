#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "${BACKUP_FILE}" ]; then
  echo "Usage: $0 <path_to_backup.sql.gz>"
  exit 1
fi

echo "[AgriScope] Restoring database from ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-agriscope_user}" "${POSTGRES_DB:-agriscope}"
echo "[AgriScope] Restore complete."
