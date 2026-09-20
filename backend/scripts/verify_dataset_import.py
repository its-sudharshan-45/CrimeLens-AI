# -*- coding: utf-8 -*-
"""
Verify crime_dataset_india.csv import integrity against the database and API layer.
"""

from __future__ import annotations

import asyncio
import io
import sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select, text

from backend.app.db.session import AsyncSessionLocal
from backend.app.models.crime_category import CrimeCategory
from backend.app.models.crime_location import CrimeLocation
from backend.app.models.crime_report import CrimeReport
from backend.app.models.prediction import Prediction
from backend.scripts.dataset_normalizer import load_and_normalize


async def verify() -> dict:
    rows, summary = load_and_normalize()
    report: dict = {"checks": [], "passed": 0, "failed": 0}

    def record(name: str, ok: bool, detail: str) -> None:
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if ok:
            report["passed"] += 1
        else:
            report["failed"] += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")

    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))

        ds_count = await session.execute(
            text("SELECT count(*) FROM crime_reports WHERE crime_number LIKE 'IND-%'")
        )
        ds_total = int(ds_count.scalar() or 0)
        record(
            "dataset_report_count",
            ds_total == summary["normalized_records"],
            f"expected {summary['normalized_records']}, found {ds_total}",
        )

        pred_count = await session.execute(
            text(
                "SELECT count(*) FROM predictions "
                "WHERE model_version = 'crime_dataset_india.csv'"
            )
        )
        pred_total = int(pred_count.scalar() or 0)
        record(
            "dataset_prediction_count",
            pred_total == summary["normalized_records"],
            f"expected {summary['normalized_records']}, found {pred_total}",
        )

        cat_result = await session.execute(select(func.count()).select_from(CrimeCategory))
        cat_total = int(cat_result.scalar() or 0)
        record(
            "categories_present",
            cat_total >= len(summary["categories"]),
            f"{cat_total} categories in DB",
        )

        loc_result = await session.execute(
            select(func.count()).select_from(CrimeLocation).where(CrimeLocation.city.in_(summary["cities"]))
        )
        loc_total = int(loc_result.scalar() or 0)
        record(
            "locations_for_cities",
            loc_total >= len(summary["cities"]),
            f"{loc_total} city locations",
        )

        # Search/filter smoke tests (SQL equivalent of repository queries)
        search = await session.execute(
            text(
                "SELECT count(*) FROM crime_reports "
                "WHERE is_deleted = false AND (title ILIKE :q OR description ILIKE :q OR crime_number ILIKE :q)"
            ),
            {"q": "%Mumbai%"},
        )
        search_total = int(search.scalar() or 0)
        record("search_by_city", search_total > 0, f"total={search_total}")

        closed = await session.execute(
            text("SELECT count(*) FROM crime_reports WHERE is_deleted = false AND status = 'CLOSED'")
        )
        closed_total = int(closed.scalar() or 0)
        record("filter_status_closed", closed_total > 0, f"total={closed_total}")

        dated = await session.execute(
            text(
                "SELECT count(*) FROM crime_reports "
                "WHERE is_deleted = false AND incident_date >= :from_dt AND incident_date <= :to_dt"
            ),
            {
                "from_dt": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "to_dt": datetime(2020, 12, 31, tzinfo=timezone.utc),
            },
        )
        dated_total = int(dated.scalar() or 0)
        record("filter_date_range_2020", dated_total > 0, f"total={dated_total}")

        sample = await session.execute(
            select(CrimeReport).where(CrimeReport.crime_number == "IND-000001")
        )
        first = sample.scalars().first()
        record("sample_report_retrieval", first is not None, "IND-000001 present" if first else "missing")

        if first:
            preds = await session.execute(
                select(Prediction).where(Prediction.report_id == first.id)
            )
            record("sample_prediction_linked", preds.scalars().first() is not None,
                   "prediction linked to IND-000001")

    report["summary"] = summary
    return report


if __name__ == "__main__":
    result = asyncio.run(verify())
    print("\n" + "=" * 60)
    print(f"Verification: {result['passed']} passed, {result['failed']} failed")
    print("=" * 60)
    sys.exit(1 if result["failed"] else 0)
