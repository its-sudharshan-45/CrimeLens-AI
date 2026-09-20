# -*- coding: utf-8 -*-
"""
Normalize legacy investigation status values in PostgreSQL (Supabase).

Maps demo/legacy labels to the current InvestigationStatus enum:
  IN_PROGRESS, ACTIVE  -> UNDER_INVESTIGATION
  ASSIGNED             -> OPEN
  COMPLETED            -> CLOSED

Run from repository root:
    python -m backend.scripts.migrate_investigation_statuses

Idempotent — safe to run multiple times.
"""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from backend.app.db.session import AsyncSessionLocal

STATUS_MAP: dict[str, str] = {
    "IN_PROGRESS": "UNDER_INVESTIGATION",
    "ACTIVE": "UNDER_INVESTIGATION",
    "ASSIGNED": "OPEN",
    "COMPLETED": "CLOSED",
}

CANONICAL_VALUES = (
    "OPEN",
    "UNDER_INVESTIGATION",
    "WAITING_FOR_EVIDENCE",
    "ON_HOLD",
    "CLOSED",
    "ARCHIVED",
)


async def _distinct_statuses(session) -> list[tuple[str, int]]:
    result = await session.execute(
        text("SELECT status::text AS status, count(*) FROM investigations GROUP BY status::text ORDER BY 2 DESC")
    )
    return [(str(row[0]), int(row[1])) for row in result.all()]


async def migrate() -> None:
    print("=" * 60)
    print("  Investigation status normalization (Supabase / PostgreSQL)")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

        before = await _distinct_statuses(session)
        print("\n[BEFORE]")
        for status, count in before:
            print(f"  {status}: {count}")

        dialect = session.bind.dialect.name if session.bind else "unknown"
        if dialect != "postgresql":
            print(f"\n[SKIP] Dialect is {dialect}; enum migration only runs on PostgreSQL.")
            return

        # Ensure canonical enum labels exist (no-op if already present)
        for value in CANONICAL_VALUES:
            await session.execute(
                text(f"ALTER TYPE investigationstatus ADD VALUE IF NOT EXISTS '{value}'")
            )
        await session.commit()

        updated_total = 0
        for old_status, new_status in STATUS_MAP.items():
            result = await session.execute(
                text(
                    """
                    UPDATE investigations
                    SET status = CAST(:new_status AS investigationstatus),
                        updated_at = NOW()
                    WHERE status::text = :old_status
                    """
                ),
                {"old_status": old_status, "new_status": new_status},
            )
            count = result.rowcount or 0
            if count:
                print(f"\n[UPDATE] {old_status} -> {new_status}: {count} row(s)")
            updated_total += count

        await session.commit()

        after = await _distinct_statuses(session)
        print("\n[AFTER]")
        for status, count in after:
            print(f"  {status}: {count}")

        print("\n" + "=" * 60)
        print(f"Done. Rows updated: {updated_total}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate())
