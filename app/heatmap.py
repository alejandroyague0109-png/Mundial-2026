# app/routers/heatmap.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathlib import Path

from app.database import get_db

router = APIRouter(tags=["Heatmap"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/heatmap", response_class=HTMLResponse)
async def view_heatmap(request: Request, db: AsyncSession = Depends(get_db)):
    
    # 1. Usuarios
    res_users = await db.execute(text("SELECT country_code, COUNT(id) FROM users GROUP BY country_code"))
    users_by_country = {str(row[0]).strip().upper(): int(row[1]) for row in res_users.all() if row[0]}

    # 2. Figuritas
    res_inv = await db.execute(text("""
        SELECT u.country_code, COUNT(i.id) 
        FROM inventory i 
        JOIN users u ON i.user_id = u.id 
        GROUP BY u.country_code
    """))
    inv_by_country = {str(row[0]).strip().upper(): int(row[1]) for row in res_inv.all() if row[0]}

    # Diccionario final
    map_data = {}
    all_countries = set(list(users_by_country.keys()) + list(inv_by_country.keys()))
    
    for c in all_countries:
        if not c: continue
        map_data[c] = {
            "users": users_by_country.get(c, 0),
            "activity": inv_by_country.get(c, 0)
        }

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })