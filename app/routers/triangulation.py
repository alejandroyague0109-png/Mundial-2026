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
    Algoritmo de Triangulación Circular (Vos -> B -> C -> Vos)
    Prioridades:
    1. Matches donde B y C tengan las figuritas en su Wishlist (Scoring).
    2. Usar Puentes (C) distintos para no saturar a un mismo usuario.
    3. Fallback: Reutilizar puentes si no hay suficientes opciones únicas.
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

    # 3. Cargar el Mercado de la ZONA (Traemos TODO para saber qué les falta)
    zone_query = (
        select(Inventory.user_id, Inventory.sticker_num, Inventory.status, User)
        .join(User)
        .where(
            User.country_code == me.country_code, # <-- NUEVO: Aislar por país
            User.province == me.province,
            User.zone == me.zone,
            User.id != current_user_id,
            Inventory.status.in_(['wishlist', 'repetida', 'repe', 'tengo']) 
        )
    )
    
    zone_res = await db.execute(zone_query)
    rows = zone_res.all()

    # 4. Construir Diccionarios en Memoria
    user_repes = defaultdict(set)
    user_wishlist = defaultdict(set)
    user_has_any = defaultdict(set)
    users_meta = {}

    for uid, s_num, status, user_obj in rows:
        users_meta[uid] = user_obj
        st = status.lower()
        if st in ['repetida', 'repe']:
            user_repes[uid].add(s_num)
            user_has_any[uid].add(s_num)
        elif st == 'tengo':
            user_has_any[uid].add(s_num)
        elif st == 'wishlist':
            user_wishlist[uid].add(s_num)

    # 5. ALGORITMO DE MATCH CIRCULAR CON SCORING
    all_possible_results = []
    seen_combinations = set()

    # Paso A: ¿Quién tiene la que YO quiero? (Estos serán los B)
    # IMPORTANTE: En la triangulación Vos->B->C->Vos, quien TIENE lo que vos querés es B.
    candidates_B = [uid for uid, repes in user_repes.items() if sticker_num in repes]

    for uid_B in candidates_B:
        # Paso B: Buscamos a C (El Puente)
        for uid_C, c_repes in user_repes.items():
            if uid_C == uid_B or uid_C == current_user_id: 
                continue

            # ¿Qué le puede dar C a B? (Algo que C tiene repetido y B NO tiene)
            possible_bridges = c_repes - user_has_any[uid_B]
            if not possible_bridges: 
                continue 

            # ¿Qué le puedo dar YO a C? (Algo que YO tengo repetido y C NO tiene)
            possible_payments = my_repes - user_has_any[uid_C]
            if not possible_payments: 
                continue

            # Selección de mejores figuritas (Priorizando Wishlist)
            best_bridge = None
            bridge_in_wishlist = False
            for b in possible_bridges:
                if b in user_wishlist[uid_B]: # B la quiere explícitamente
                    best_bridge = b
                    bridge_in_wishlist = True
                    break
            if not best_bridge:
                best_bridge = list(possible_bridges)[0]

            best_payment = None
            payment_in_wishlist = False
            for p in possible_payments:
                if p in user_wishlist[uid_C]: # C la quiere explícitamente
                    best_payment = p
                    payment_in_wishlist = True
                    break
            if not best_payment:
                best_payment = list(possible_payments)[0]

            score = 0
            if bridge_in_wishlist: score += 1
            if payment_in_wishlist: score += 1

            combo_key = (uid_B, uid_C)
            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                
                user_B = users_meta[uid_B]
                user_C = users_meta[uid_C]
                
                all_possible_results.append({
                    "score": score,
                    "target_sticker": {
                        "num": sticker_num,
                        "name": format_sticker(sticker_num)
                    },
                    "my_payment_sticker": {
                        "num": best_payment,
                        "name": format_sticker(best_payment),
                        "is_wishlist": payment_in_wishlist
                    },
                    "bridge_sticker": {
                        "num": best_bridge,
                        "name": format_sticker(best_bridge),
                        "is_wishlist": bridge_in_wishlist
                    },
                    "user_B": {
                        "id": user_B.id,
                        "nick": user_B.nick,
                        "phone": decrypt_phone(user_B.phone_hash) if user_B.phone_hash else ""
                    },
                    "user_C": {
                        "id": user_C.id,
                        "nick": user_C.nick,
                        "phone": decrypt_phone(user_C.phone_hash) if user_C.phone_hash else ""
                    }
                })

    # 6. FILTRADO Y CONSOLIDACIÓN (Prioridad a Puentes Únicos + Score)
    
    # Primero ordenamos todo el pool global por Score (Los mejores arriba)
    all_possible_results.sort(key=lambda x: x["score"], reverse=True)
    
    primary_results = [] # Tienen puente (C) único
    backup_results = []  # El puente (C) ya fue usado en un primary_result
    used_bridge_ids = set()

    for res in all_possible_results:
        bridge_id = res["user_C"]["id"]
        
        # Como ya están ordenados por Score, el primero que entra de un Puente es su mejor match
        if bridge_id not in used_bridge_ids:
            primary_results.append(res)
            used_bridge_ids.add(bridge_id)
        else:
            backup_results.append(res)

    # Llenamos la lista final priorizando los primarios
    final_results = primary_results[:3]
    
    # Si no llegamos a 3 con puentes únicos, rellenamos con los backups (que también tienen alto score)
    backup_index = 0
    while len(final_results) < 3 and backup_index < len(backup_results):
        final_results.append(backup_results[backup_index])
        backup_index += 1

    return JSONResponse(content={"found": len(final_results) > 0, "results": final_results})