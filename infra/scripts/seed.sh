#!/usr/bin/env bash
set -euo pipefail

echo "[AgriScope] Seeding initial database tables and reference crops..."
docker compose exec -T api python -m app.db.init_db
echo "[AgriScope] Seeding complete."
