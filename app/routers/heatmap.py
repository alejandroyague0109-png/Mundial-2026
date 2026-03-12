# app/routers/heatmap.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from app.database import get_db
from app.models import User, Inventory

router = APIRouter(tags=["Heatmap"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/heatmap", response_class=HTMLResponse)
async def view_heatmap(request: Request, db: AsyncSession = Depends(get_db)):
    
    # 1. Obtenemos cantidad de usuarios por país
    res_users = await db.execute(
        select(User.country_code, func.count(User.id))
        .group_by(User.country_code)
    )
    users_by_country = {row[0]: row[1] for row in res_users.all() if row[0]}

    # 2. Obtenemos cantidad de figuritas en el sistema (actividad) por país
    res_inv = await db.execute(
        select(User.country_code, func.count(Inventory.id))
        .join(User, User.id == Inventory.user_id)
        .group_by(User.country_code)
    )
    inv_by_country = {row[0]: row[1] for row in res_inv.all() if row[0]}

    # Construimos el diccionario final para el frontend
    # Google GeoCharts usa códigos ISO (AR, MX, CO...)
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()))
    
    for c in all_countries:
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0)
        }

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })