# -*- coding: utf-8 -*-
"""
Create investigations for open dataset crime reports (Case Closed = No in CSV).

Derived from crime_dataset_india.csv via imported IND-* reports — not synthetic evidence.
Idempotent via stable UUIDs and ON CONFLICT DO NOTHING.

Run:
    python -m backend.scripts.import_investigations_from_dataset
"""

from __future__ import annotations

import asyncio
import io
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.session import AsyncSessionLocal

_NS = uuid.UUID("d4e5f6a7-b8c9-0123-def4-567890abcdef")
BATCH = 200
NOW = datetime.now(timezone.utc)


def _uid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)


async def import_investigations() -> None:
    from backend.app.models.crime_report import CrimeReport
    from backend.app.models.investigation import Investigation
    from backend.app.models.user import User

    print("=" * 60)
    print("  Import investigations from dataset (open IND-* reports)")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        users = await session.execute(
            select(User.id).where(
                or_(User.email.like("%inv.%"), User.email.like("%officer%"))
            )
        )
        investigator_ids = [row[0] for row in users.all()]
        if not investigator_ids:
            res = await session.execute(select(User.id).limit(1))
            investigator_ids = [res.scalar_one()]

        result = await session.execute(
            select(
                CrimeReport.id,
                CrimeReport.crime_number,
                CrimeReport.status,
                CrimeReport.priority,
                CrimeReport.report_date,
                CrimeReport.title,
            ).where(
                CrimeReport.crime_number.like("IND-%"),
                CrimeReport.is_deleted.is_(False),
                CrimeReport.status.in_(("OPEN", "UNDER_INVESTIGATION")),
            )
        )
        reports = list(result.all())
        print(f"\n[LOAD] {len(reports)} open dataset reports eligible for investigation")

        rows = []
        for i, (report_id, crime_number, status, priority, report_date, title) in enumerate(reports):
            inv_status = status if status in ("OPEN", "UNDER_INVESTIGATION") else "OPEN"
            assigned_at = report_date or NOW
            rows.append(
                {
                    "id": _uid(f"inv:dataset:{crime_number}"),
                    "report_id": report_id,
                    "investigator_id": investigator_ids[i % len(investigator_ids)],
                    "notes": (
                        f"[SOURCE: crime_dataset_india.csv] Auto-opened for open case "
                        f"{crime_number}: {title[:120]}"
                    ),
                    "status": inv_status,
                    "priority": priority,
                    "assigned_at": assigned_at,
                    "closed_at": None,
                    "resolution_summary": None,
                    "created_at": assigned_at,
                    "updated_at": NOW,
                    "deleted_at": None,
                }
            )

        inserted = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            stmt = pg_insert(Investigation.__table__).values(batch).on_conflict_do_nothing(
                index_elements=["id"]
            )
            result = await session.execute(stmt)
            inserted += result.rowcount or 0
        await session.commit()

        total = await session.execute(
            text(
                "SELECT count(*) FROM investigations i "
                "JOIN crime_reports r ON r.id = i.report_id "
                "WHERE r.crime_number LIKE 'IND-%'"
            )
        )
        print(f"[DONE] Inserted {inserted} new investigations")
        print(f"[DONE] Total dataset-linked investigations: {int(total.scalar() or 0)}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(import_investigations())
