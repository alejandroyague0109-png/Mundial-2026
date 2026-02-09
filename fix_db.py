import asyncio
from sqlalchemy import text
from app.database import engine

async def fix_foreign_key_constraint():
    async with engine.begin() as conn:
        print("🔧 Actualizando restricciones de clave foránea en 'contact_logs'...")
        
        # 1. Identificar y borrar la restricción actual (el nombre suele variar, así que intentamos el estándar)
        # Nota: En Postgres las FK suelen llamarse 'tabla_columna_fkey'
        try:
            await conn.execute(text("""
                ALTER TABLE contact_logs 
                DROP CONSTRAINT IF EXISTS contact_logs_inventory_id_fkey;
            """))
            print("✅ Restricción antigua eliminada.")
        except Exception as e:
            print(f"⚠️ Aviso al borrar constraint: {e}")

        # 2. Crear la nueva restricción con ON DELETE CASCADE
        await conn.execute(text("""
            ALTER TABLE contact_logs 
            ADD CONSTRAINT contact_logs_inventory_id_fkey 
            FOREIGN KEY (inventory_id) 
            REFERENCES inventory(id) 
            ON DELETE CASCADE;
        """))
        print("✅ Nueva restricción con CASCADE aplicada.")

    print("🚀 Base de datos lista para completar intercambios.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_foreign_key_constraint())