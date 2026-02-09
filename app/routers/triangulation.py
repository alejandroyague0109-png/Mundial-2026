from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from collections import defaultdict
import random

from app.database import get_db
from app.models import User, Inventory
from app.data_album import ALBUM_STRUCTURE
from app.utils import decrypt_phone

router = APIRouter(tags=["Triangulation"])

# --- HELPER: Formatear nombre (Ej: 10 -> ARG 10) ---
def format_sticker(sticker_num):
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            local_num = sticker_num - data["start"] + 1
            return f"{code} {local_num}"
    return f"#{sticker_num}"

@router.get("/triangulation/search")
async def search_triangulation(
    sticker_num: int, 
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    """
    Algoritmo de Triangulación Híbrido:
    1. Busca: VOS -> C -> B -> VOS.
    2. Prioridad: Puentes (C) distintos.
    3. Fallback: Si no hay 3 puentes distintos, reutiliza puentes para completar 3 opciones.
    """
    
    # 1. Validaciones de Usuario
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie: 
        return JSONResponse({"message": "Inicia sesión"}, status_code=401)
    
    current_user_id = int(user_id_cookie)
    me_res = await db.execute(select(User).where(User.id == current_user_id))
    me = me_res.scalars().first()
    
    if not me or not me.is_premium:
        return JSONResponse({"message": "Función exclusiva para Premium"}, status_code=403)
    
    if not me.zone or not me.province:
        return JSONResponse({"message": "Configurá tu zona en el perfil"}, status_code=400)

    # 2. Cargar mi inventario disponible para dar (MIS REPETIDAS)
    my_repes_res = await db.execute(select(Inventory.sticker_num).where(
        Inventory.user_id == current_user_id,
        Inventory.status.in_(['repetida', 'repe'])
    ))
    my_repes = set(my_repes_res.scalars().all())

    if not my_repes:
        return JSONResponse({"message": "No tenés repetidas para intercambiar."}, status_code=400)

    # 3. Cargar el Mercado de la ZONA
    zone_query = (
        select(Inventory.user_id, Inventory.sticker_num, Inventory.status, User)
        .join(User)
        .where(
            User.province == me.province,
            User.zone == me.zone,
            User.id != current_user_id,
            Inventory.status.in_(['wishlist', 'repetida', 'repe'])
        )
    )
    
    zone_res = await db.execute(zone_query)
    rows = zone_res.all()

    # 4. Construir Grafos en Memoria
    user_has = defaultdict(set)
    user_wants = defaultdict(set)
    users_meta = {}

    for uid, s_num, status, user_obj in rows:
        users_meta[uid] = user_obj
        st = status.lower()
        if st in ['repetida', 'repe']:
            user_has[uid].add(s_num)
        elif st == 'wishlist':
            user_wants[uid].add(s_num)

    # 5. ALGORITMO DE BÚSQUEDA HÍBRIDO
    primary_results = [] # Resultados con puentes ÚNICOS
    backup_results = []  # Resultados con puentes REPETIDOS
    used_bridge_ids = set()
    
    # Buscar candidatos B (Dueños)
    possible_Bs = []
    for uid, stickers in user_has.items():
        if sticker_num in stickers:
            possible_Bs.append(uid)
    
    random.shuffle(possible_Bs)

    for uid_B in possible_Bs:
        # Optimización: Si ya tenemos 3 puentes únicos, paramos.
        if len(primary_results) >= 3: break
        
        wants_of_B = user_wants[uid_B]
        if not wants_of_B: continue

        # Buscar candidatos C (Puentes)
        potential_Cs = list(user_has.keys())
        random.shuffle(potential_Cs) # Mezclar para variedad

        for uid_C in potential_Cs:
            if uid_C == uid_B: continue 
            
            # Match C -> B
            stickers_C_has = user_has[uid_C]
            match_C_gives_B = stickers_C_has.intersection(wants_of_B)
            
            if match_C_gives_B:
                # Match Yo -> C
                wants_of_C = user_wants[uid_C]
                match_A_gives_C = wants_of_C.intersection(my_repes)

                if match_A_gives_C:
                    # ¡Triangulación encontrada!
                    sticker_bridge = list(match_C_gives_B)[0]
                    sticker_payment = list(match_A_gives_C)[0]
                    
                    user_B = users_meta[uid_B]
                    user_C = users_meta[uid_C]

                    triangulation_data = {
                        "target_sticker": {
                            "num": sticker_num,
                            "name": format_sticker(sticker_num)
                        },
                        "my_payment_sticker": {
                            "num": sticker_payment,
                            "name": format_sticker(sticker_payment)
                        },
                        "bridge_sticker": {
                            "num": sticker_bridge,
                            "name": format_sticker(sticker_bridge)
                        },
                        "user_B": {
                            "id": user_B.id,
                            "nick": user_B.nick,
                            "phone": decrypt_phone(user_B.phone_hash)
                        },
                        "user_C": {
                            "id": user_C.id,
                            "nick": user_C.nick,
                            "phone": decrypt_phone(user_C.phone_hash)
                        }
                    }
                    
                    # CLASIFICACIÓN DE RESULTADO
                    if uid_C not in used_bridge_ids:
                        primary_results.append(triangulation_data)
                        used_bridge_ids.add(uid_C)
                    else:
                        backup_results.append(triangulation_data)
                    
                    # Rompemos aquí para pasar al siguiente B.
                    # Esto asegura variedad de Dueños (B).
                    break 

    # 6. CONSOLIDACIÓN FINAL (Llenar hasta 3)
    final_results = primary_results
    
    while len(final_results) < 3 and len(backup_results) > 0:
        final_results.append(backup_results.pop(0))
    
    # Cortar por seguridad si nos pasamos (aunque el break lo evita)
    final_results = final_results[:3]

    return JSONResponse(content={"found": len(final_results) > 0, "results": final_results})