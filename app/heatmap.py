# app/routers/heatmap.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from app.database import get_db
from app.models import User, Inventory, ContactLog

router = APIRouter(tags=["Heatmap"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/heatmap", response_class=HTMLResponse)
async def view_heatmap(request: Request, db: AsyncSession = Depends(get_db)):
    
    # 1. Usuarios
    res_users = await db.execute(
        select(User.country_code, func.count(User.id)).group_by(User.country_code)
    )
    users_by_country = {str(row[0]).strip().upper(): int(row[1]) for row in res_users.all() if row[0]}

    # 2. Figuritas
    res_inv = await db.execute(
        select(User.country_code, func.count(Inventory.id))
        .join(User, User.id == Inventory.user_id)
        .group_by(User.country_code)
    )
    inv_by_country = {str(row[0]).strip().upper(): int(row[1]) for row in res_inv.all() if row[0]}

    # 3. Intercambios (Traemos todo crudo agrupado)
    res_trades = await db.execute(
        select(ContactLog.country_code, ContactLog.status, func.count(ContactLog.id))
        .group_by(ContactLog.country_code, ContactLog.status)
    )
    all_trades = res_trades.all()
    
    trades_by_country = {}
    debug_mensajes = [] # Guardaremos acá lo que ve la DB para mandarlo a la pantalla
    
    for code, status, count in all_trades:
        c = str(code).strip().upper() if code else 'AR'
        s = str(status).strip().lower() if status else 'null'
        cantidad = int(count)
        
        debug_mensajes.append(f"[{c} - {s}: {cantidad}]")
        
        if s in ['completed', 'pending']:
            trades_by_country[c] = trades_by_country.get(c, 0) + cantidad

    # Construimos el texto de depuración
    texto_debug = " | ".join(debug_mensajes) if debug_mensajes else "🚨 LA TABLA CONTACT_LOGS ESTÁ VACÍA EN ESTA BASE DE DATOS 🚨"

    # Diccionario final
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()) + list(trades_by_country.keys()))
    
    for c in all_countries:
        if not c: continue
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0),
            "trades": trades_by_country.get(c, 0)
        }

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data,
        "debug_info": texto_debug  # <--- Enviamos el scanner a la pantalla
    })