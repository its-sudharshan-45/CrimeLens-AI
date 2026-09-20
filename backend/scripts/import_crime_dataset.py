# -*- coding: utf-8 -*-
# cspell:disable
"""
CrimeLens AI — Import crime_dataset_india.csv into the application database.

Run from repository root:
    python -m backend.scripts.import_crime_dataset

Idempotent: uses stable crime_number (IND-######) and ON CONFLICT DO NOTHING.
Does NOT fabricate Investigation or Evidence records from CSV fields.
"""

from __future__ import annotations

import asyncio
import io
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.db.session import AsyncSessionLocal
from backend.scripts.dataset_normalizer import (
    CATEGORY_DEFS,
    load_and_normalize,
    location_record,
    write_normalized_artifacts,
)

_NS = uuid.UUID("c3d4e5f6-a7b8-9012-cdef-123456789012")
BATCH_SIZE = 200
IN_CLAUSE_BATCH = 1000
NOW = datetime.now(timezone.utc)


def _uid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, name)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


async def _upsert_batch(session, table, rows: list[dict], conflict_cols: list[str]) -> int:
    if not rows:
        return 0
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        stmt = pg_insert(table).values(batch).on_conflict_do_nothing(index_elements=conflict_cols)
        result = await session.execute(stmt)
        inserted += result.rowcount or 0
    return inserted


async def _count(session, table_name: str) -> int:
    result = await session.execute(text(f'SELECT count(*) FROM "{table_name}"'))
    return int(result.scalar() or 0)


async def import_dataset() -> dict[str, Any]:
    from backend.app.models.crime_category import CrimeCategory
    from backend.app.models.crime_location import CrimeLocation
    from backend.app.models.crime_report import CrimeReport
    from backend.app.models.prediction import Prediction
    from backend.app.models.user import User

    print("=" * 70)
    print("  CrimeLens AI — crime_dataset_india.csv Import")
    print("=" * 70)

    rows, summary = load_and_normalize()
    jsonl_path, summary_path = write_normalized_artifacts(rows, summary)
    print(f"\n[ANALYZE] Source records : {summary['source_records']}")
    print(f"          Normalized     : {summary['normalized_records']}")
    print(f"          Skipped        : {summary['skipped_records']}")
    print(f"          Cities         : {len(summary['cities'])}")
    print(f"          Categories     : {len(summary['categories'])}")
    print(f"          Artifact       : {jsonl_path.name}")
    print(f"          Summary        : {summary_path.name}")

    stats: dict[str, Any] = {
        "summary": summary,
        "inserted": {},
        "existing_before": {},
        "existing_after": {},
    }

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
        print("\n[OK] Database connection verified")

        for tbl in ["crime_categories", "crime_locations", "crime_reports", "predictions"]:
            stats["existing_before"][tbl] = await _count(session, tbl)

        # Users required for reporter_id
        result = await session.execute(select(User.id, User.email))
        users = list(result.all())
        if not users:
            print("\n[ERROR] No users found. Run: python -m backend.scripts.seed_db")
            return stats

        reporter_ids = [
            uid
            for uid, email in users
            if any(token in email for token in ("officer", "inv.", "admin"))
        ] or [users[0][0]]

        # Categories
        print("\n[1/4] Upserting crime categories...")
        cat_rows = []
        for name, (severity, color, desc) in CATEGORY_DEFS.items():
            cat_rows.append(
                {
                    "id": _uid(f"cat:dataset:{name}"),
                    "name": name,
                    "description": desc,
                    "severity_level": severity,
                    "color_code": color,
                    "created_at": NOW,
                    "updated_at": NOW,
                    "deleted_at": None,
                }
            )
        stats["inserted"]["categories"] = await _upsert_batch(
            session, CrimeCategory.__table__, cat_rows, ["name"]
        )
        await session.commit()

        result = await session.execute(select(CrimeCategory.id, CrimeCategory.name))
        cat_map = {name: cid for cid, name in result.all()}

        # Locations — one canonical location per city in the dataset
        print("[2/4] Upserting crime locations...")
        loc_rows = []
        for city in summary["cities"]:
            loc = location_record(city, NOW)
            loc_rows.append({"id": _uid(f"loc:dataset:{city}"), **loc})
        stats["inserted"]["locations"] = await _upsert_batch(
            session, CrimeLocation.__table__, loc_rows, ["id"]
        )
        await session.commit()

        result = await session.execute(select(CrimeLocation.id, CrimeLocation.city))
        city_loc_map = {city: lid for lid, city in result.all()}

        # Crime reports
        print("[3/4] Importing crime reports (batched)...")
        report_rows = []
        report_meta: list[dict[str, Any]] = []
        skipped_mapping = 0

        for idx, row in enumerate(rows):
            cat_id = cat_map.get(row["category_name"])
            loc_id = city_loc_map.get(row["city"])
            if not cat_id or not loc_id:
                skipped_mapping += 1
                continue

            incident_dt = _parse_dt(row["incident_date"])
            report_dt = _parse_dt(row["report_date"])
            reporter_id = reporter_ids[idx % len(reporter_ids)]
            report_id = _uid(f"report:dataset:{row['report_number']}")

            report_rows.append(
                {
                    "id": report_id,
                    "crime_number": row["crime_number"],
                    "title": row["title"],
                    "description": row["description"],
                    "incident_date": incident_dt,
                    "report_date": report_dt,
                    "status": row["status"],
                    "priority": row["priority"],
                    "victim_count": row["victim_count"],
                    "suspect_count": row["suspect_count"],
                    "estimated_loss": row["estimated_loss"],
                    "reporter_id": reporter_id,
                    "category_id": cat_id,
                    "location_id": loc_id,
                    "created_at": report_dt,
                    "updated_at": NOW,
                    "deleted_at": None,
                }
            )
            report_meta.append(
                {
                    "id": report_id,
                    "crime_number": row["crime_number"],
                    "report_number": row["report_number"],
                    "reporter_id": reporter_id,
                    "incident_date": incident_dt,
                    "report_date": report_dt,
                    "normalized": row,
                }
            )

        stats["skipped_mapping"] = skipped_mapping
        stats["inserted"]["reports"] = await _upsert_batch(
            session, CrimeReport.__table__, report_rows, ["crime_number"]
        )
        await session.commit()

        # Resolve report ids from DB (handles re-runs) — batched IN queries
        crime_numbers = [m["crime_number"] for m in report_meta]
        db_report_map: dict[str, Any] = {}
        for i in range(0, len(crime_numbers), IN_CLAUSE_BATCH):
            chunk = crime_numbers[i : i + IN_CLAUSE_BATCH]
            result = await session.execute(
                select(CrimeReport.id, CrimeReport.crime_number).where(
                    CrimeReport.crime_number.in_(chunk)
                )
            )
            db_report_map.update({cn: rid for rid, cn in result.all()})

        # Predictions — derived from dataset crime labels (not synthetic investigations)
        print("[4/4] Importing AI predictions from dataset labels...")
        pred_rows = []
        for meta in report_meta:
            report_id = db_report_map.get(meta["crime_number"])
            if not report_id:
                continue
            norm = meta["normalized"]
            pred_dt = meta["report_date"]
            label = norm["crime_description"].title()

            pred_rows.append(
                {
                    "id": _uid(f"pred:dataset:{norm['report_number']}"),
                    "report_id": report_id,
                    "user_id": meta["reporter_id"],
                    "prediction_label": label,
                    "prediction_type": "CRIME_TYPE",
                    "confidence_score": 1.0,
                    "model_name": "DatasetGroundTruth",
                    "model_version": "crime_dataset_india.csv",
                    "prediction_time": pred_dt,
                    "execution_time_ms": 0,
                    "explanation": (
                        "Ground-truth crime type imported from crime_dataset_india.csv "
                        f"(Report #{norm['report_number']})."
                    ),
                    "raw_output": {
                        "source": "crime_dataset_india.csv",
                        "report_number": norm["report_number"],
                        "crime_code": norm["crime_code"],
                        "crime_description": norm["crime_description"],
                        "crime_domain": norm["crime_domain"],
                        "city": norm["city"],
                        "weapon_used": norm["weapon_used"],
                        "victim_age": norm["victim_age"],
                        "victim_gender": norm["victim_gender"],
                        "police_deployed": norm["police_deployed"],
                        "case_closed": norm["case_closed"],
                        "raw_fields": norm["raw"],
                    },
                    "created_at": pred_dt,
                    "updated_at": pred_dt,
                    "deleted_at": None,
                }
            )

        stats["inserted"]["predictions"] = await _upsert_batch(
            session, Prediction.__table__, pred_rows, ["id"]
        )
        await session.commit()

        for tbl in ["crime_categories", "crime_locations", "crime_reports", "predictions"]:
            stats["existing_after"][tbl] = await _count(session, tbl)

        dataset_reports = await session.execute(
            text("SELECT count(*) FROM crime_reports WHERE crime_number LIKE 'IND-%'")
        )
        stats["dataset_reports_in_db"] = int(dataset_reports.scalar() or 0)

        print("\n" + "=" * 70)
        print("IMPORT COMPLETE")
        print("=" * 70)
        print(f"  Categories inserted : {stats['inserted'].get('categories', 0)}")
        print(f"  Locations inserted  : {stats['inserted'].get('locations', 0)}")
        print(f"  Reports inserted    : {stats['inserted'].get('reports', 0)}")
        print(f"  Predictions inserted: {stats['inserted'].get('predictions', 0)}")
        print(f"  Dataset reports in DB (IND-*): {stats['dataset_reports_in_db']}")
        print("=" * 70)
        print("\nNOTE: Investigations and Evidence were NOT generated from CSV fields.")
        print("      Those sections remain empty unless separate synthetic seed data exists.")

    return stats


if __name__ == "__main__":
    asyncio.run(import_dataset())
