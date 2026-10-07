"""Seed 1M prediction rows for performance testing.

Usage:
  python infra/scripts/seed_predictions.py --rows 1000000
  AGRISCOPE_DB_URL=postgresql+asyncpg://... python infra/scripts/seed_predictions.py --rows 1000000
"""
from __future__ import annotations

import argparse
import asyncio
import os
import random
import uuid
from datetime import datetime, timedelta

SEED_USER_ID = "00000000-0000-0000-0000-000000000001"
SEED_EMAIL = "seed@agriscope.dev"
ET_CLASSES = ["low", "moderate", "high"]
SOURCES = ["manual", "location", "batch", "api"]


async def ensure_seed_user(conn) -> None:
    from sqlalchemy import text

    await conn.execute(
        text("""
            INSERT INTO users (id, email, full_name, hashed_password, role, plan,
                               is_active, is_verified, created_at, updated_at)
            VALUES (:id, :email, 'Seed User', 'x', 'user', 'pro', true, true,
                    NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        {"id": SEED_USER_ID, "email": SEED_EMAIL},
    )


async def seed(rows: int, db_url: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(db_url, echo=False, pool_size=5)
    batch_size = 5_000
    inserted = 0
    base_date = datetime(2020, 1, 1)

    print(f"Seeding {rows:,} prediction rows in batches of {batch_size:,}…")

    async with engine.begin() as conn:
        await ensure_seed_user(conn)

    async with engine.begin() as conn:
        for start in range(0, rows, batch_size):
            count = min(batch_size, rows - start)
            records = []
            for i in range(count):
                idx = start + i
                et = round(random.uniform(1.0, 9.0), 3)
                margin = round(random.uniform(0.2, 0.8), 3)
                records.append({
                    "id": str(uuid.uuid4()),
                    "user_id": SEED_USER_ID,
                    "et_value": et,
                    "et_low": round(et - margin, 3),
                    "et_high": round(et + margin, 3),
                    "source": random.choice(SOURCES),
                    "classification": random.choice(ET_CLASSES),
                    "input_data": (
                        '{"temp_max":30,"temp_min":18,'
                        '"humidity":60,"wind_speed":2.5}'
                    ),
                    "is_saved": random.random() < 0.05,
                    "timestamp": (base_date + timedelta(seconds=idx * 30)).isoformat(),
                })

            await conn.execute(
                text("""
                    INSERT INTO predictions
                        (id, user_id, et_value, et_low, et_high, source,
                         classification, input_data, is_saved, timestamp)
                    VALUES
                        (:id, :user_id, :et_value, :et_low, :et_high, :source,
                         :classification, :input_data, :is_saved, :timestamp)
                """),
                records,
            )
            inserted += count
            if inserted % 50_000 == 0:
                print(f"  {inserted:,} / {rows:,} rows inserted…")

    await engine.dispose()
    print(f"✓ Done — {inserted:,} prediction rows seeded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed AgriScope prediction rows.")
    parser.add_argument("--rows", type=int, default=100_000, help="Number of rows to insert")
    args = parser.parse_args()
    db_url = os.environ.get(
        "AGRISCOPE_DB_URL",
        "postgresql+asyncpg://agriscope:agriscope@localhost:5432/agriscope",
    )
    asyncio.run(seed(args.rows, db_url))
