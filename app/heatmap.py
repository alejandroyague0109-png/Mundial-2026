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
    print("=== INICIANDO CARGA DE DATOS PARA EL MAPA ===")
    
    # 1. Usuarios por país
    res_users = await db.execute(
        select(User.country_code, func.count(User.id)).group_by(User.country_code)
    )
    users_by_country = {row[0]: int(row[1]) for row in res_users.all() if row[0]}

    # 2. Figuritas en el sistema
    res_inv = await db.execute(
        select(User.country_code, func.count(Inventory.id))
        .join(User, User.id == Inventory.user_id)
        .group_by(User.country_code)
    )
    inv_by_country = {row[0]: int(row[1]) for row in res_inv.all() if row[0]}

    # =========================================================
    # DEBUG: INVESTIGACIÓN DE LA TABLA CONTACT_LOGS
    # =========================================================
    # A. Ver qué estados hay realmente guardados y cuántos son
    debug_status = await db.execute(select(ContactLog.status, func.count(ContactLog.id)).group_by(ContactLog.status))
    print(f"🔍 DEBUG 1 (Estados en DB): {debug_status.all()}")

    # B. Ver los países guardados en los ContactLogs
    debug_countries = await db.execute(select(ContactLog.country_code, func.count(ContactLog.id)).group_by(ContactLog.country_code))
    print(f"🔍 DEBUG 2 (Países en Trades): {debug_countries.all()}")
    # =========================================================

    # 3. Intercambios realizados
    res_trades = await db.execute(
        select(ContactLog.country_code, func.count(ContactLog.id))
        # Agregamos func.trim() por si los estados se guardaron con espacios por error (ej: "pending ")
        .where(func.trim(ContactLog.status).in_(['completed', 'pending'])) 
        .group_by(ContactLog.country_code)
    )
    
    trades_result = res_trades.all()
    print(f"🔄 DEBUG 3 (Resultado Query Trades filtrados): {trades_result}")

    # Cuidado: Si country_code es None, en lugar de ignorarlo, lo vamos a mandar a "AR" por defecto para no perderlo.
    trades_by_country = {}
    for row in trades_result:
        pais = row[0] if row[0] else 'AR'
        cantidad = int(row[1])
        if pais in trades_by_country:
            trades_by_country[pais] += cantidad
        else:
            trades_by_country[pais] = cantidad
            
    print(f"📊 DEBUG 4 (Diccionario de Transacciones): {trades_by_country}")

    # Construimos el diccionario final para el frontend
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()) + list(trades_by_country.keys()))
    
    for c in all_countries:
        # Aseguramos que la clave no sea vacía
        if not c: continue
        
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0),
            "trades": trades_by_country.get(c, 0)
        }

    print(f"🚀 DATA FINAL ENVIADA AL FRONTEND: {map_data}")
    print("=============================================")

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })