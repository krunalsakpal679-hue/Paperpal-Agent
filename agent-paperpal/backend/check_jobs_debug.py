import asyncio
import sys
import os

# Add parent dir to path
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.database import sessionmanager
from app.models.job import Job
from app.config import settings

async def check_jobs():
    sessionmanager.init(settings.DATABASE_URL)
    async with sessionmanager.session_factory() as session:
        res = await session.execute(select(Job).order_by(Job.created_at.desc()).limit(10))
        jobs = res.scalars().all()
        print(f"Total jobs requested: {len(jobs)}")
        for j in jobs:
            print(f"ID: {j.id}, Status: {j.status}, Journal: {j.journal_identifier}, Created: {j.created_at}")
    await sessionmanager.close()

if __name__ == "__main__":
    asyncio.run(check_jobs())
