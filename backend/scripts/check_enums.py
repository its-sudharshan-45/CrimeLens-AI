# cspell:disable
import asyncio
from backend.app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        for enum_name in ["investigationstatus", "crimestatus", "priority", "evidencetype"]:
            try:
                q = f"SELECT unnest(enum_range(NULL::{enum_name}))::text"
                r = await s.execute(text(q))
                vals = [row[0] for row in r.all()]
                print(f"{enum_name}: {vals}")
            except Exception as e:
                print(f"{enum_name}: ERROR - {e}")

asyncio.run(check())
