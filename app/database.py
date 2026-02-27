import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Obtenemos la URL
DATABASE_URL = os.getenv("SUPABASE_URL_SQLALCHEMY")

if not DATABASE_URL:
    # Si estás usando la versión hardcodeada, comenta las líneas de arriba y descomenta esta:
    # DATABASE_URL = "postgresql+asyncpg://postgres.jgbryjupuuqqcrfruxcy:Alito.251018@aws-0-us-west-2.pooler.supabase.com:6543/postgres"
    raise ValueError("❌ Error: No se encontró SUPABASE_URL_SQLALCHEMY en el .env")

# Creamos el motor con el FIX para Supabase Transaction Pooler
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    future=True,
    pool_pre_ping=True,  # 🪄 MAGIA 1: Verifica que la conexión esté viva antes de usarla
    pool_recycle=1800,    # 🪄 MAGIA 2: Recicla las conexiones cada 30 minutos (1800 segs) para que no queden viejas
    connect_args={
        "statement_cache_size": 0
    }
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()