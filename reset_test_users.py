import asyncio
import random
from sqlalchemy import select, delete, or_
from app.database import AsyncSessionLocal, engine, Base
from app.models import User, Inventory, ContactUnlock
from app.utils import hash_password, encrypt_phone

# --- DATOS DE PRUEBA ---
USERS_DATA = [
    {"nick": "Luz",   "phone": "2604301018", "premium": True,  "province": "Mendoza", "zone": "Capital (Mendoza)"},
    {"nick": "Alito", "phone": "2604672372", "premium": False, "province": "Mendoza", "zone": "Capital (Mendoza)"},
    {"nick": "El 10", "phone": "2604672371", "premium": False, "province": "Mendoza", "zone": "Capital (Mendoza)"},
    {"nick": "El 11", "phone": "2604672370", "premium": False, "province": "Mendoza", "zone": "Capital (Mendoza)"},
    {"nick": "El 12", "phone": "2604672373", "premium": False, "province": "Mendoza", "zone": "Godoy Cruz"},
    {"nick": "El 13", "phone": "2604672374", "premium": False, "province": "Mendoza", "zone": "Guaymallén"},
]

COMMON_PASSWORD = "hola"
COMMON_SECRET_Q = "Equipo favorito"
COMMON_SECRET_A = "river"

async def reset_users():
    print("🚀 Iniciando script de regeneración de usuarios...")
    
    async with AsyncSessionLocal() as db:
        for u_data in USERS_DATA:
            print(f"🔄 Procesando usuario: {u_data['nick']}...")

            # 1. Calcular credenciales seguras
            phone_enc = encrypt_phone(u_data["phone"])
            pwd_hash = hash_password(COMMON_PASSWORD)
            ans_hash = hash_password(COMMON_SECRET_A)

            # 2. BUSCAR Y LIMPIAR (Fix IntegrityError)
            # Primero buscamos el ID del usuario si existe
            stmt_find = select(User).where(
                or_(User.nick == u_data["nick"], User.phone_hash == phone_enc)
            )
            result = await db.execute(stmt_find)
            existing_user = result.scalars().first()

            if existing_user:
                print(f"   🗑️  Eliminando datos previos de {existing_user.nick}...")
                
                # A. Borrar Inventario (Hijos)
                await db.execute(delete(Inventory).where(Inventory.user_id == existing_user.id))
                
                # B. Borrar Historial de Desbloqueos (Hijos)
                # Borramos donde aparezca como Viewer o como Target
                await db.execute(delete(ContactUnlock).where(
                    or_(ContactUnlock.user_id == existing_user.id, ContactUnlock.target_user_id == existing_user.id)
                ))
                
                # C. Finalmente, borrar al Usuario (Padre)
                await db.execute(delete(User).where(User.id == existing_user.id))
                await db.commit()

            # 3. CREAR USUARIO NUEVO
            new_user = User(
                nick=u_data["nick"],
                phone_hash=phone_enc,
                password=pwd_hash,
                province=u_data["province"],
                zone=u_data["zone"],
                secret_question=COMMON_SECRET_Q,
                secret_answer=ans_hash,
                is_premium=u_data["premium"],
                reputation=random.randint(1, 5),
                daily_contacts_count=0
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            # 4. CARGAR FIGURITAS (INVENTARIO)
            inventory = []
            
            # a) Figuritas Repetidas (Para canje) - IDs 1 a 30
            for i in range(5):
                sticker = random.randint(1, 100)
                inventory.append(Inventory(
                    user_id=new_user.id,
                    sticker_num=sticker,
                    status="repetida",
                    quantity=2,
                    price=0
                ))

            # b) Figuritas en Venta (Precio > 0) - IDs 101 a 150
            for i in range(3):
                sticker = random.randint(101, 200)
                inventory.append(Inventory(
                    user_id=new_user.id,
                    sticker_num=sticker,
                    status="repetida",
                    quantity=1,
                    price=random.choice([500, 1000, 2000])
                ))

            # c) Wishlist (Lo que buscan)
            for i in range(5):
                sticker = random.randint(1, 100) 
                inventory.append(Inventory(
                    user_id=new_user.id,
                    sticker_num=sticker,
                    status="wishlist",
                    quantity=0,
                    price=0
                ))

            db.add_all(inventory)
            await db.commit()
            print(f"✅ {u_data['nick']} creado con {len(inventory)} items.")

    print("\n✨ ¡Proceso finalizado con éxito!")
    print(f"Password general: {COMMON_PASSWORD}")

if __name__ == "__main__":
    asyncio.run(reset_users())