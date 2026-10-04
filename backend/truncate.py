import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def main():
    db_url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("TRUNCATE TABLE subscriber, incident_updates, incident_services, incident, service, \"user\" CASCADE;"))

if __name__ == "__main__":
    asyncio.run(main())
