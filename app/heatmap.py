# app/routers/heatmap.py
import sys
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
    print("=== INICIANDO CARGA DE DATOS PARA EL MAPA ===", flush=True)
    
    # 1. Usuarios por país
    res_users = await db.execute(
        select(User.country_code, func.count(User.id)).group_by(User.country_code)
    )
    users_by_country = {row[0]: int(row[1]) for row in res_users.all() if row[0]}

    # 2. Figuritas
    res_inv = await db.execute(
        select(User.country_code, func.count(Inventory.id))
        .join(User, User.id == Inventory.user_id)
        .group_by(User.country_code)
    )
    inv_by_country = {row[0]: int(row[1]) for row in res_inv.all() if row[0]}

    # 3. Intercambios (Traemos TODO y filtramos en Python para evitar bugs de SQL)
    res_trades_all = await db.execute(
        select(ContactLog.country_code, ContactLog.status, func.count(ContactLog.id))
        .group_by(ContactLog.country_code, ContactLog.status)
    )
    all_trades = res_trades_all.all()
    
    print(f"🔍 DEBUG CONTACT_LOGS (DB Cruda): {all_trades}", flush=True)
    
    trades_by_country = {}
    for row in all_trades:
        pais = row[0] if row[0] else 'AR'
        # Limpiamos espacios y pasamos a minúscula por las dudas
        estado = str(row[1]).strip().lower() if row[1] else ''
        cantidad = int(row[2])
        
        # Filtramos manualmente los exitosos/pendientes
        if estado in ['completed', 'pending']:
            trades_by_country[pais] = trades_by_country.get(pais, 0) + cantidad
            
    print(f"📊 DEBUG DICCIONARIO TRADES: {trades_by_country}", flush=True)

    # Construimos el diccionario final
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()) + list(trades_by_country.keys()))
    
    for c in all_countries:
        if not c: continue # Salto de seguridad
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0),
            "trades": trades_by_country.get(c, 0)
        }

    print(f"🚀 DATA FINAL: {map_data}", flush=True)

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })