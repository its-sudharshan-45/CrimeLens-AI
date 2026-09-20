import asyncio, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.db.session import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as s:
        for tbl in ['users','crime_categories','crime_locations','crime_reports','investigations','investigation_assignments','investigation_notes','investigation_timeline','evidence','predictions','audit_logs']:
            try:
                r = await s.execute(text(f'SELECT count(*) FROM "{tbl}"'))
                print(f'{tbl}: {r.scalar()}')
            except Exception as e:
                print(f'{tbl}: ERROR - {e}')

asyncio.run(check())
