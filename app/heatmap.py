# app/routers/heatmap.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from app.database import get_db
# Importación vital: los modelos nativos
from app.models import User, Inventory

router = APIRouter(tags=["Heatmap"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/heatmap", response_class=HTMLResponse)
async def view_heatmap(request: Request, db: AsyncSession = Depends(get_db)):
    
    # 1. Usuarios (Usando ORM para evitar fallos de lectura SQL)
    query_users = (
        select(User.country_code, User.province, func.count(User.id))
        .group_by(User.country_code, User.province)
    )
    res_users = await db.execute(query_users)
    
    # 2. Figuritas (Usando ORM)
    query_inv = (
        select(User.country_code, User.province, func.count(Inventory.id))
        .join(User, Inventory.user_id == User.id)
        .group_by(User.country_code, User.province)
    )
    res_inv = await db.execute(query_inv)

    map_data = {}

    # Procesar Usuarios
    for country_code, province_name, count in res_users.all():
        country = str(country_code).strip().upper() if country_code else "Desconocido"
        province = str(province_name).strip() if province_name else "Desconocida"
        c = int(count) if count else 0
        
        if country not in map_data:
            map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
            
        map_data[country]["total_users"] += c
        
        if province not in map_data[country]["provinces"]:
            map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
            
        map_data[country]["provinces"][province]["users"] += c

    # Procesar Figuritas
    for country_code, province_name, count in res_inv.all():
        country = str(country_code).strip().upper() if country_code else "Desconocido"
        province = str(province_name).strip() if province_name else "Desconocida"
        c = int(count) if count else 0
        
        if country not in map_data:
            map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
            
        map_data[country]["total_activity"] += c
        
        if province not in map_data[country]["provinces"]:
            map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
            
        map_data[country]["provinces"][province]["activity"] += c

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })