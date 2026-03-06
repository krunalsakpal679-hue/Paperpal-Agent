import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from app.database import get_session
from app.models.journal import Journal
from sqlalchemy import select

async def main():
    async with get_session() as s:
        res = await s.execute(select(Journal))
        journals = res.scalars().all()
        print(f"Journals in DB: {[j.identifier for j in journals]}")

if __name__ == "__main__":
    asyncio.run(main())
