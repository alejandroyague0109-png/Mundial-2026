from fastapi import APIRouter, Depends, Request, Form, Response, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pathlib import Path

from app.database import get_db
from app.models import User, Inventory
from app.data_album import ALBUM_STRUCTURE
from app.utils import parse_smart_input
from app.locations import ARGENTINA

# --- NUEVO IMPORT ---
from app.services.notifications import notify_wishlist_match 
# --------------------

router = APIRouter(tags=["Album"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def format_sticker(sticker_num):
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            local_num = sticker_num - data["start"] + 1
            return f"{code} {local_num}"
    return f"#{sticker_num}"

templates.env.globals['format_sticker'] = format_sticker

# --- HELPER: CALCULAR ESTADÍSTICAS ---
async def calculate_user_stats(user_id: int, db: AsyncSession):
    # ... (TU CÓDIGO DE ESTADÍSTICAS SE MANTIENE IGUAL) ...
    result_stats = await db.execute(select(Inventory.status).where(Inventory.user_id == user_id))
    all_statuses = result_stats.scalars().all()
    
    count_tengo = all_statuses.count("tengo")
    count_repetida = all_statuses.count("repetida")
    
    pegadas = count_tengo + count_repetida
    total_stickers = sum(d['count'] for d in ALBUM_STRUCTURE.values())
    faltan = total_stickers - pegadas
    if faltan < 0: faltan = 0

    return {
        "tengo": pegadas,           
        "repetidas": count_repetida,
        "faltan": faltan,           
        "total": total_stickers,
        "porcentaje": int((pegadas / total_stickers) * 100) if total_stickers > 0 else 0
    }

# --- 1. VISTA PRINCIPAL (EL MARCO/SHELL) ---
@router.get("/album", response_class=HTMLResponse)
async def view_album(request: Request, db: AsyncSession = Depends(get_db)):
    # ... (TU CÓDIGO SE MANTIENE IGUAL) ...
    user_id = request.cookies.get("user_id")
    if not user_id: return RedirectResponse(url="/login", status_code=303)

    result_user = await db.execute(select(User).where(User.id == int(user_id)))
    user = result_user.scalars().first()
    if not user: 
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("user_id")
        return response

    stats = await calculate_user_stats(user.id, db)
    first_code = list(ALBUM_STRUCTURE.keys())[0]

    return templates.TemplateResponse("album.html", {
        "request": request,
        "user": user,
        "album_structure": ALBUM_STRUCTURE,
        "locations": ARGENTINA,
        "stats": stats,
        "first_country_code": first_code,
        "active_tab": "album"
    })

# --- 2. VISTA DE UN PAÍS (GRILLA + TABLA) ---
@router.get("/country/{country_code}")
async def get_country_view(request: Request, country_code: str, db: AsyncSession = Depends(get_db)):
    # ... (TU CÓDIGO SE MANTIENE IGUAL) ...
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)

    info = ALBUM_STRUCTURE.get(country_code)
    if not info: return Response(status_code=404)

    start = info["start"]
    end = start + info["count"] - 1
    
    result = await db.execute(
        select(Inventory)
        .where(Inventory.user_id == int(user_id), Inventory.sticker_num >= start, Inventory.sticker_num <= end)
        .order_by(Inventory.sticker_num)
    )
    items = result.scalars().all()
    
    return templates.TemplateResponse("partials/country_view.html", {
        "request": request,
        "info": info,
        "code": country_code,
        "inventory": {item.sticker_num: item for item in items},
        "repeated_items": [item for item in items if item.status == "repetida"],
        "country_start_index": start,
        "range": range
    })

# --- 3. CARGA RÁPIDA ---
@router.post("/quick_load")
async def process_quick_load(
    request: Request,
    country_code: str = Form(...),
    tengo_txt: str = Form(""),
    repes_txt: str = Form(""),
    wish_txt: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    # ... (TU CÓDIGO SE MANTIENE IGUAL POR AHORA) ...
    # Nota: Aquí también podrías agregar notificaciones si alguien carga repes masivamente,
    # pero para la prueba nos centramos en el clic individual.
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)
    user_id = int(user_id)

    info = ALBUM_STRUCTURE.get(country_code)
    if not info: return Response(status_code=404)
    
    start_global = info["start"]
    count = info["count"]
    end_global = start_global + count - 1

    ids_tengo = parse_smart_input(tengo_txt, start_global, count)
    ids_repes = parse_smart_input(repes_txt, start_global, count)
    ids_wish = parse_smart_input(wish_txt, start_global, count)

    final_tengo = ids_tengo.union(ids_repes)
    final_wish = ids_wish - final_tengo

    await db.execute(
        delete(Inventory).where(
            Inventory.user_id == user_id, 
            Inventory.sticker_num >= start_global, 
            Inventory.sticker_num <= end_global
        )
    )

    new_rows = []
    for num in (final_tengo - ids_repes):
        new_rows.append(Inventory(user_id=user_id, sticker_num=num, status="tengo", quantity=1))
    for num in ids_repes:
        new_rows.append(Inventory(user_id=user_id, sticker_num=num, status="repetida", quantity=2))
    for num in final_wish:
        new_rows.append(Inventory(user_id=user_id, sticker_num=num, status="wishlist", quantity=0))

    if new_rows: db.add_all(new_rows)
    await db.commit()

    response_html = (await get_country_view(request, country_code, db)).body.decode("utf-8")
    
    stats = await calculate_user_stats(user_id, db)
    stats_html = templates.TemplateResponse("partials/stats_bar.html", {"request": request, "stats": stats, "oob": True}).body.decode("utf-8")

    response = HTMLResponse(content=response_html + stats_html)
    response.headers["HX-Trigger"] = "closeModal"
    return response

# --- 4. LÓGICA DE CLICKS (MODIFICADA CON NOTIFICACIÓN) ---
@router.post("/sticker/{sticker_num}")
async def toggle_sticker(
    request: Request, 
    sticker_num: int, 
    # BackgroundTasks: Permite enviar el mensaje sin congelar la pantalla del usuario
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db)
):
    user_id = int(request.cookies.get("user_id"))
    
    # 1. Recuperamos al Usuario Dueño (Necesario para el nombre en la notificación)
    user_res = await db.execute(select(User).where(User.id == user_id))
    current_user = user_res.scalars().first()

    # A. Actualizar DB
    result = await db.execute(select(Inventory).where(Inventory.user_id == user_id, Inventory.sticker_num == sticker_num))
    item = result.scalars().first()

    should_notify = False # Bandera para saber si disparamos la alerta

    if not item:
        item = Inventory(user_id=user_id, sticker_num=sticker_num, status="tengo", quantity=1)
        db.add(item)
    else:
        # Ciclo de estados: Tengo -> Repetida -> Wishlist -> Nada (Borrar)
        if item.status == "tengo":
            item.status = "repetida"
            item.quantity = 2
            # 🔥 AQUÍ ES EL MOMENTO MÁGICO 🔥
            # El usuario acaba de marcar que tiene una REPETIDA. ¡Avisemos!
            should_notify = True
            
        elif item.status == "repetida":
            item.status = "wishlist"; item.quantity = 0; item.price = 0
        elif item.status == "wishlist":
            await db.delete(item); item = None
    
    await db.commit()
    if item: await db.refresh(item)

    # DISPARAR NOTIFICACIÓN EN SEGUNDO PLANO
    if should_notify and current_user:
        sticker_name = format_sticker(sticker_num)
        # Usamos background_tasks para que la UI responda instantáneo
        # y Telegram se envíe por detrás.
        background_tasks.add_task(
            notify_wishlist_match, 
            db, 
            sticker_num, 
            sticker_name, 
            current_user
        )

    # B. Calcular datos del país
    country_start = 0
    info = None
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            country_start = data["start"]
            info = data
            break
    
    local_num = sticker_num - country_start + 1 if country_start > 0 else sticker_num

    # C. Renderizar CARTA
    card_html = templates.TemplateResponse("partials/sticker_card.html", {
        "request": request, "num": sticker_num, 
        "local_num": local_num,
        "status": item.status if item else "falta", 
        "item": item
    }).body.decode("utf-8")

    # D. Renderizar TABLA DE REPETIDAS
    table_html = ""
    if info:
        result_repes = await db.execute(
            select(Inventory).where(
                Inventory.user_id == user_id,
                Inventory.status == "repetida",
                Inventory.sticker_num >= info["start"],
                Inventory.sticker_num < info["start"] + info["count"]
            ).order_by(Inventory.sticker_num)
        )
        table_html = templates.TemplateResponse("partials/repeated_table.html", {
            "request": request,
            "repeated_items": result_repes.scalars().all(),
            "oob": True
        }).body.decode("utf-8")

    # E. Renderizar STATS BAR
    stats = await calculate_user_stats(user_id, db)
    stats_html = templates.TemplateResponse("partials/stats_bar.html", {
        "request": request, "stats": stats, "oob": True
    }).body.decode("utf-8")

    return HTMLResponse(content=card_html + table_html + stats_html)

# --- (EL RESTO DEL ARCHIVO SIGUE IGUAL: batch_country_action, update_item_details) ---
@router.post("/country/{country_code}/{action}")
async def batch_country_action(request: Request, country_code: str, action: str, db: AsyncSession = Depends(get_db)):
    # ... (TU CÓDIGO ORIGINAL SIN CAMBIOS) ...
    user_id = int(request.cookies.get("user_id"))
    country_data = ALBUM_STRUCTURE.get(country_code)
    start = country_data["start"]
    end = start + country_data["count"] - 1
    
    await db.execute(
        delete(Inventory).where(
            Inventory.user_id == user_id, 
            Inventory.sticker_num >= start, 
            Inventory.sticker_num <= end
        )
    )
    if action == "all":
        db.add_all([Inventory(user_id=user_id, sticker_num=num, status="tengo", quantity=1) for num in range(start, end + 1)])
    await db.commit()

    response_html = (await get_country_view(request, country_code, db)).body.decode("utf-8")
    stats = await calculate_user_stats(user_id, db)
    stats_html = templates.TemplateResponse("partials/stats_bar.html", {"request": request, "stats": stats, "oob": True}).body.decode("utf-8")
    return HTMLResponse(content=response_html + stats_html)

@router.post("/update_item/{sticker_num}")
async def update_item_details(
    request: Request, sticker_num: int, 
    price: int = Form(None), quantity: int = Form(None), 
    db: AsyncSession = Depends(get_db)
):
    # ... (TU CÓDIGO ORIGINAL SIN CAMBIOS) ...
    user_id = int(request.cookies.get("user_id"))
    result = await db.execute(select(Inventory).where(Inventory.user_id == user_id, Inventory.sticker_num == sticker_num))
    item = result.scalars().first()
    
    if item:
        if price is not None: item.price = price
        if quantity is not None: item.quantity = quantity
        await db.commit()
        await db.refresh(item)

        country_start = 0
        for code, data in ALBUM_STRUCTURE.items():
            if data["start"] <= sticker_num < data["start"] + data["count"]:
                country_start = data["start"]
                break
        local_num = sticker_num - country_start + 1

        return templates.TemplateResponse("partials/sticker_card.html", {
            "request": request, "num": sticker_num, 
            "local_num": local_num,
            "status": item.status, "item": item,
            "force_oob": True 
        })
    return Response(status_code=200)