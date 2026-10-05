import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def main():
    try:
        engine = create_async_engine("postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")
        async with engine.connect() as conn:
            print("Connected to PostgreSQL on 5432 with password 'postgres'!")
    except Exception as e:
        print("Failed to connect:", e)
asyncio.run(main())
