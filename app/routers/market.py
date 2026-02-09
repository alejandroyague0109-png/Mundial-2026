from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from pathlib import Path
from collections import defaultdict
from datetime import date
import json
from pydantic import BaseModel

from app.database import get_db
from app.models import User, Inventory, ContactLog
from app.locations import ARGENTINA
from app.data_album import ALBUM_STRUCTURE 

# --- IMPORTACIÓN DE UTILIDADES ---
try:
    from app.utils import decrypt_phone
except ImportError:
    def decrypt_phone(x): return ""
# ------------------------

router = APIRouter(tags=["Market"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- SCHEMAS ACTUALIZADO ---
class CompleteTransactionSchema(BaseModel):
    given_sticker_num: int = 0  # Cambiamos str por int (0 si no entregó nada)

# --- HELPER: FORMATO ---
def format_sticker(sticker_num):
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            local_num = sticker_num - data["start"] + 1
            return f"{code} {local_num}"
    return f"#{sticker_num}"

# --- HELPER: PARSER ---
def parse_sticker_query(query_str: str):
    if not query_str: return None
    clean_q = query_str.strip().upper().replace("-", " ") 
    
    if clean_q.isdigit():
        return {"type": "single", "value": int(clean_q)}
    
    parts = clean_q.split()
    
    if len(parts) == 1:
        code = parts[0]
        if code in ALBUM_STRUCTURE:
            data = ALBUM_STRUCTURE[code]
            return {
                "type": "range", 
                "min": data["start"], 
                "max": data["start"] + data["count"]
            }

    if len(parts) >= 2 and parts[1].isdigit():
        code = parts[0]
        local_num = int(parts[1])
        if code in ALBUM_STRUCTURE:
            data = ALBUM_STRUCTURE[code]
            if 1 <= local_num <= data["count"]:
                val = data["start"] + local_num - 1
                return {"type": "single", "value": val}
                
    return None

# --- ENDPOINTS ---

@router.get("/market", response_class=HTMLResponse)
async def market_view(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    if not user: return RedirectResponse(url="/login", status_code=303)

    # --- NUEVO: Obtener Wishlist para el modal de Triangulación ---
    wishlist_query = select(Inventory).where(
        Inventory.user_id == user.id,
        Inventory.status == 'wishlist'
    ).order_by(Inventory.sticker_num)
    
    wishlist_res = await db.execute(wishlist_query)
    wishlist_items = wishlist_res.scalars().all()

    # Formateamos la lista para el HTML: [{num: 10, name: 'ARG 10'}, ...]
    wishlist_formatted = []
    for item in wishlist_items:
        wishlist_formatted.append({
            "num": item.sticker_num,
            "name": format_sticker(item.sticker_num)
        })
    # -------------------------------------------------------------

    return templates.TemplateResponse("market.html", {
        "request": request,
        "user": user,
        "locations": ARGENTINA,
        "active_tab": "market",
        "album_structure": ALBUM_STRUCTURE,
        "wishlist": wishlist_formatted  # <--- Pasamos la lista al template
    })

@router.get("/market/zones_options")
async def get_zones_options(province: str = ""):
    if not province or province not in ARGENTINA:
        return HTMLResponse("<option value=''>Todas las zonas</option>")
    options = "<option value=''>Todas las zonas</option>"
    for zone in ARGENTINA[province]:
        options += f"<option value='{zone}'>{zone}</option>"
    return HTMLResponse(options)

# --- CONTACTO SEGURO Y REGISTRO DE TRANSACCIÓN ---
@router.post("/market/contact/{item_id}")
async def contact_item(item_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie:
        return JSONResponse(content={"message": "Debes iniciar sesión"}, status_code=401)
    
    current_user_id = int(user_id_cookie)
    current_user = await db.get(User, current_user_id)
    if not current_user:
        return JSONResponse(content={"message": "Usuario no encontrado"}, status_code=404)

    item = await db.get(Inventory, item_id)
    if not item:
        return JSONResponse(content={"message": "La figurita ya no existe"}, status_code=404)
    
    owner = await db.get(User, item.user_id)
    if not owner or not owner.phone_hash:
        return JSONResponse(content={"message": "El dueño no tiene datos de contacto"}, status_code=404)

    if owner.id == current_user.id:
        return JSONResponse(content={"message": "No podés negociar con vos mismo"}, status_code=400)

    existing_log_res = await db.execute(select(ContactLog).where(
        ContactLog.user_id == current_user.id,
        ContactLog.inventory_id == item.id,
        ContactLog.status == 'pending'
    ))
    existing_log = existing_log_res.scalars().first()

    if not existing_log:
        today = date.today()
        if current_user.last_contact_date != today:
            current_user.daily_contacts_count = 0
            current_user.last_contact_date = today
            await db.commit() 
        
        if not current_user.is_premium:
            if current_user.daily_contacts_count >= 1:
                return JSONResponse(
                    content={"message": "Has alcanzado tu límite de 1 contacto diario."}, 
                    status_code=403
                )
            current_user.daily_contacts_count += 1
        
        new_log = ContactLog(
            user_id=current_user.id,
            target_id=owner.id,
            inventory_id=item.id,
            status='pending'
        )
        db.add(new_log)
        await db.commit()
    
    real_phone = decrypt_phone(owner.phone_hash)
    return {"phone": real_phone, "status": "success"}

# --- GESTIÓN DE TRANSACCIONES (OPCIONES) ---

@router.post("/market/log/{log_id}/fairplay")
async def fair_play(log_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie: return JSONResponse({}, 401)
    
    log = await db.get(ContactLog, log_id)
    if not log or log.user_id != int(user_id_cookie):
        return JSONResponse({"message": "Transacción inválida"}, 404)
    
    if log.rating is not None:
        return JSONResponse({"message": "Ya calificaste esta transacción"}, 400)

    target_user = await db.get(User, log.target_id)
    if target_user:
        target_user.reputation += 1
        log.rating = 1
        await db.commit()
        return {"status": "success", "new_reputation": target_user.reputation}
    
    return JSONResponse({"message": "Usuario no encontrado"}, 404)

@router.post("/market/log/{log_id}/cancel")
async def cancel_transaction(log_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie: return JSONResponse({}, 401)

    log = await db.get(ContactLog, log_id)
    if not log or log.user_id != int(user_id_cookie):
        return JSONResponse({"message": "Transacción inválida"}, 404)

    log.status = 'cancelled'
    await db.commit()
    return {"status": "success"}

@router.post("/market/log/{log_id}/complete")
async def complete_transaction(
    log_id: int, 
    payload: CompleteTransactionSchema,
    request: Request, 
    db: AsyncSession = Depends(get_db)
):
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie: return JSONResponse({}, 401)
    current_user_id = int(user_id_cookie)

    try:
        log = await db.get(ContactLog, log_id)
        if not log or log.user_id != current_user_id:
            return JSONResponse({"message": "Transacción inválida"}, 404)

        # 1. Sumar la figurita recibida
        original_item = await db.get(Inventory, log.inventory_id)
        sticker_num_to_add = 0
        if original_item:
            sticker_num_to_add = original_item.sticker_num
        
        # (Aquí podrías agregar lógica fallback si original_item es None, pero por ahora lo dejamos simple)

        if sticker_num_to_add > 0:
            my_item_res = await db.execute(select(Inventory).where(
                Inventory.user_id == current_user_id,
                Inventory.sticker_num == sticker_num_to_add
            ))
            my_item = my_item_res.scalars().first()

            if my_item:
                my_item.status = 'tengo'
                # Opcional: si ya la tenías y recibís otra, podrías sumar quantity y marcar como repe.
                # Pero en un canje normal, asumimos que la recibís porque te faltaba.
            else:
                new_item = Inventory(
                    user_id=current_user_id,
                    sticker_num=sticker_num_to_add,
                    status='tengo',
                    quantity=1
                )
                db.add(new_item)

        # 2. Restar la entregada (CON LOGICA DE CAMBIO DE ESTADO)
        if payload.given_sticker_num > 0:
            my_given_res = await db.execute(select(Inventory).where(
                Inventory.user_id == current_user_id,
                Inventory.sticker_num == payload.given_sticker_num,
                func.lower(Inventory.status).in_(['repetida', 'repe'])
            ))
            my_given_item = my_given_res.scalars().first()
            
            if my_given_item:
                if my_given_item.quantity > 2:
                    # Caso A: Tenía 3 o más. Resto 1. Sigue siendo > 1, así que sigue siendo "repetida".
                    my_given_item.quantity -= 1
                
                elif my_given_item.quantity == 2:
                    # Caso B: Tenía 2. Resto 1. Me queda 1.
                    # CRÍTICO: Esa que queda YA NO ES REPE, es la mía.
                    my_given_item.quantity = 1
                    my_given_item.status = 'tengo' 
                
                else:
                    # Caso C: Tenía 1 marcada como repe (raro, pero posible si forzó el sistema).
                    # Si la entrega, se queda sin nada.
                    await db.delete(my_given_item)

        # 3. Completar
        log.status = 'completed'
        await db.commit()

        return {"status": "success"}

    except Exception as e:
        await db.rollback()
        print(f"Error completando transacción: {e}")
        return JSONResponse({"message": "Error interno al procesar"}, 500)

# --- BÚSQUEDA HÍBRIDA (INCLUYE PENDIENTES) ---
@router.get("/market/search", response_class=HTMLResponse)
async def search_market(
    request: Request,
    province: str = "",
    zone: str = "",
    nick: str = "",
    sticker_num: str = "", 
    db: AsyncSession = Depends(get_db)
):
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie: return HTMLResponse("Inicia sesión")
    current_user_id = int(user_id_cookie)

    result_user = await db.execute(select(User).where(User.id == current_user_id))
    current_user_obj = result_user.scalars().first()
    
    # --- CONTEXTO MEJORADO: CARGAMOS MIS REPETIDAS PARA EL SELECT ---
    # Buscamos todas mis repetidas con detalle
    my_dupes_query = select(Inventory).where(
        Inventory.user_id == current_user_id,
        Inventory.status.in_(['repetida', 'repe'])
    ).order_by(Inventory.sticker_num)
    
    my_dupes_res = await db.execute(my_dupes_query)
    my_dupes_list = []
    for item in my_dupes_res.scalars().all():
        my_dupes_list.append({
            "sticker_num": item.sticker_num,
            "name": format_sticker(item.sticker_num),
            "qty": item.quantity
        })
    # -------------------------------------------------------------

    context_data = {
        "request": request, 
        "user": current_user_obj,           
        "locations": ARGENTINA,         
        "album_structure": ALBUM_STRUCTURE,
        "my_duplicates_json": json.dumps(my_dupes_list) # Pasamos la lista al template
    }

    final_pool = []

    # FASE 0: PENDIENTES
    pending_query = (
        select(ContactLog, Inventory, User)
        .join(Inventory, ContactLog.inventory_id == Inventory.id)
        .join(User, ContactLog.target_id == User.id)
        .where(
            ContactLog.user_id == current_user_id,
            ContactLog.status == 'pending'
        )
        .order_by(ContactLog.created_at.desc())
    )
    
    pending_res = await db.execute(pending_query)
    pending_rows = pending_res.all()

    for log, item, owner in pending_rows:
        real_phone = decrypt_phone(owner.phone_hash) if owner.phone_hash else ""
        
        card_obj = {
            "id": item.id,
            "log_id": log.id, 
            "sticker_num_raw": item.sticker_num,
            "sticker_name": format_sticker(item.sticker_num),
            "price": item.price,
            "is_sale": item.price > 0,
            "is_pending": True,
            "rating_given": log.rating is not None, 
            "owner": {
                "id": owner.id,
                "nick": owner.nick,
                "phone": real_phone,
                "initial": owner.nick[0].upper() if owner.nick else "?",
                "province": owner.province,
                "reputation": owner.reputation,
                "is_premium": owner.is_premium
            },
            "matches": [], 
            "has_match": False
        }
        final_pool.append(card_obj)


    # FASE 1: MERCADO
    search_intent = parse_sticker_query(sticker_num)
    
    my_wish_res = await db.execute(select(Inventory.sticker_num).where(
        Inventory.user_id == current_user_id, 
        Inventory.status.ilike('wishlist')
    ))
    my_wishlist_ids = my_wish_res.scalars().all() or [-1]

    my_repes_res = await db.execute(select(Inventory.sticker_num).where(
        Inventory.user_id == current_user_id, 
        Inventory.status.in_(['repetida', 'repe']) 
    ))
    my_repes_ids = my_repes_res.scalars().all() or [-1]

    my_held_res = await db.execute(select(Inventory.sticker_num).where(
        Inventory.user_id == current_user_id,
        func.lower(Inventory.status).in_(['tengo', 'repetida', 'repe'])
    ))
    my_held_ids = my_held_res.scalars().all()

    distinct_query = (
        select(Inventory.sticker_num)
        .join(User)
        .where(
            Inventory.status.in_(['repetida', 'repe']), 
            Inventory.user_id != current_user_id
        )
        .distinct() 
    )

    if my_held_ids:
        distinct_query = distinct_query.where(Inventory.sticker_num.notin_(my_held_ids))
    if province:
        distinct_query = distinct_query.where(User.province == province)
    if zone:
        distinct_query = distinct_query.where(User.zone == zone)
    if nick:
        distinct_query = distinct_query.where(User.nick.ilike(f"%{nick}%"))
    
    if search_intent:
        if search_intent["type"] == "single":
            distinct_query = distinct_query.where(Inventory.sticker_num == search_intent["value"])
        elif search_intent["type"] == "range":
            distinct_query = distinct_query.where(
                Inventory.sticker_num >= search_intent["min"],
                Inventory.sticker_num < search_intent["max"]
            )

    distinct_query = distinct_query.order_by(Inventory.sticker_num.asc())
    distinct_query = distinct_query.limit(30) 

    distinct_res = await db.execute(distinct_query)
    found_sticker_ids = distinct_res.scalars().all()

    if found_sticker_ids:
        full_query = (
            select(Inventory, User)
            .join(User)
            .where(
                Inventory.sticker_num.in_(found_sticker_ids),
                Inventory.status.in_(['repetida', 'repe']),
                Inventory.user_id != current_user_id
            )
        )
        if province: full_query = full_query.where(User.province == province)
        if zone: full_query = full_query.where(User.zone == zone)
        if nick: full_query = full_query.where(User.nick.ilike(f"%{nick}%"))

        full_res = await db.execute(full_query)
        all_rows = full_res.all()

        all_owner_ids = list(set([row.User.id for row in all_rows]))
        matches_map = defaultdict(list)

        if all_owner_ids and my_repes_ids != [-1]:
            others_have_query = select(Inventory.user_id, Inventory.sticker_num).where(
                Inventory.user_id.in_(all_owner_ids),
                func.lower(Inventory.status).in_(['tengo', 'repetida', 'repe']),
                Inventory.sticker_num.in_(my_repes_ids)
            )
            batch_res = await db.execute(others_have_query)
            
            others_have_map = defaultdict(set)
            for uid, s_num in batch_res.all():
                others_have_map[uid].add(s_num)
                
            for uid in all_owner_ids:
                needed = [s for s in my_repes_ids if s not in others_have_map[uid]]
                matches_map[uid] = needed[:3]

        grouped_cards = defaultdict(list)
        for row in all_rows:
            item = row.Inventory
            owner = row.User
            
            is_already_pending = any(p.get('id') == item.id for p in final_pool)
            if is_already_pending:
                continue

            user_matches = matches_map.get(owner.id, [])
            formatted_matches = [{"name": format_sticker(m)} for m in user_matches]
            
            card_obj = {
                "id": item.id,
                "sticker_num_raw": item.sticker_num,
                "sticker_name": format_sticker(item.sticker_num),
                "price": item.price,
                "is_sale": item.price > 0,
                "is_wishlist": item.sticker_num in my_wishlist_ids,
                "is_pending": False,
                "owner": {
                    "id": owner.id,
                    "nick": owner.nick,
                    "phone": None, 
                    "initial": owner.nick[0].upper() if owner.nick else "?",
                    "province": owner.province,
                    "reputation": owner.reputation,
                    "is_premium": owner.is_premium
                },
                "matches": formatted_matches,
                "has_match": len(formatted_matches) > 0
            }
            grouped_cards[item.sticker_num].append(card_obj)

        market_pool = []
        for s_id in found_sticker_ids:
            cards = grouped_cards[s_id]
            if not cards: continue
            cards.sort(key=lambda x: (x['owner']['is_premium'], x['has_match'], x['owner']['reputation']), reverse=True)
            market_pool.extend(cards[:3])

        market_pool.sort(key=lambda x: (
            x.get('has_match', False), 
            (int(x['owner'].get('is_premium', False)) * 2) + int(x.get('is_wishlist', False)), 
            x['owner'].get('reputation', 0),
            -x.get('sticker_num_raw', 0)
        ), reverse=True)
        
        final_pool.extend(market_pool)

    context_data["cards_json"] = json.dumps(final_pool)
    return templates.TemplateResponse("partials/market_list.html", context_data)