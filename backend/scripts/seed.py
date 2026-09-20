import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings  # noqa: E402 # isort: skip
from app.models.crime_category import CrimeCategory  # noqa: E402 # isort: skip

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Seed Crime Categories
        categories_data = [
            {"name": "Theft", "severity_level": 2},
            {"name": "Robbery", "severity_level": 3},
            {"name": "Assault", "severity_level": 4},
            {"name": "Cyber Crime", "severity_level": 3},
            {"name": "Drug Crime", "severity_level": 4},
            {"name": "Kidnapping", "severity_level": 5},
            {"name": "Murder", "severity_level": 5},
            {"name": "Fraud", "severity_level": 2},
            {"name": "Domestic Violence", "severity_level": 4},
            {"name": "Missing Person", "severity_level": 4}
        ]
        
        print("Seeding crime categories...")
        for cat_data in categories_data:
            stmt = select(CrimeCategory).where(
                CrimeCategory.name == cat_data["name"]
            )
            result = await session.execute(stmt)
            existing = result.scalars().first()
            if not existing:
                cat = CrimeCategory(**cat_data)
                session.add(cat)
            
        await session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
