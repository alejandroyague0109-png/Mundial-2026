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
    
    # 1. Usuarios por país
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

    # 3. Intercambios (Conteo 100% blindado en Python para evitar fallos de SQL)
    # Traemos todos los estados y países de la tabla
    res_trades = await db.execute(select(ContactLog.country_code, ContactLog.status))
    
    trades_by_country = {}
    for row in res_trades.all():
        pais = str(row[0]).strip().upper() if row[0] else 'AR'
        # Convertimos todo a minúscula y sacamos espacios fantasma
        estado = str(row[1]).strip().lower() if row[1] else ''
        
        # Filtramos manualmente
        if estado in ['completed', 'pending']:
            trades_by_country[pais] = trades_by_country.get(pais, 0) + 1

    # Construimos el diccionario final
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()) + list(trades_by_country.keys()))
    
    for c in all_countries:
        if not c: continue 
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0),
            "trades": trades_by_country.get(c, 0)
        }

    # Imprimimos en Railway de forma forzada para auditoría
    print(f"DATOS ENVIADOS -> Usr: {users_by_country} | Fig: {inv_by_country} | Canjes: {trades_by_country}", flush=True)

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })