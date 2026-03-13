import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool  # <-- IMPORTAMOS NULLPOOL
from dotenv import load_dotenv

load_dotenv()

# Obtenemos la URL
DATABASE_URL = os.getenv("SUPABASE_URL_SQLALCHEMY")

if not DATABASE_URL:
    raise ValueError("❌ Error: No se encontró SUPABASE_URL_SQLALCHEMY en el .env")

# Creamos el motor optimizado para Supabase Transaction Pooler
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    # 🪄 MAGIA DEFINITIVA: Desactiva el pool local. 
    # Abre y cierra la conexión al instante, evitando los TimeoutErrors por saturación.
    poolclass=NullPool,  
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