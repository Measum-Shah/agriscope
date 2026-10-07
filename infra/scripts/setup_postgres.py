import asyncio
import asyncpg

async def setup():
    conn = await asyncpg.connect(
        user='postgres',
        password='postgres',
        host='127.0.0.1',
        port=5432,
        database='postgres'
    )
    
    # Check if agriscope_user exists
    user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'agriscope_user'")
    if not user_exists:
        await conn.execute("CREATE USER agriscope_user WITH PASSWORD 'agriscope_dev_password' SUPERUSER")
        print('Created agriscope_user')
    else:
        await conn.execute("ALTER USER agriscope_user WITH PASSWORD 'agriscope_dev_password' SUPERUSER")
        print('agriscope_user updated')

    # Check if database agriscope exists
    db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'agriscope'")
    if not db_exists:
        await conn.execute("CREATE DATABASE agriscope OWNER agriscope_user")
        print('Created database agriscope')
    else:
        print('Database agriscope already exists')
    await conn.close()

    # Enable postgis extension if available
    db_conn = await asyncpg.connect(
        user='postgres',
        password='postgres',
        host='127.0.0.1',
        port=5432,
        database='agriscope'
    )
    try:
        await db_conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        print("PostGIS extension enabled")
    except Exception as e:
        print("PostGIS notice:", e)
    await db_conn.close()

if __name__ == '__main__':
    asyncio.run(setup())
