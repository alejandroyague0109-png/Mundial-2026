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
    
    query_users = (
        select(User.country_code, User.province, func.count(User.id))
        .group_by(User.country_code, User.province)
    )
    res_users = await db.execute(query_users)
    
    query_inv = (
        select(User.country_code, User.province, func.count(Inventory.id))
        .join(User, Inventory.user_id == User.id)
        .group_by(User.country_code, User.province)
    )
    res_inv = await db.execute(query_inv)

    map_data = {}

    # CORRECCIÓN VITAL: Iterar con índices para evitar crasheos de SQLAlchemy
    for row in res_users.all():
        country = str(row[0]).strip().upper() if row[0] else "Desconocido"
        province = str(row[1]).strip() if row[1] else "Desconocida"
        c = int(row[2]) if row[2] else 0
        
        if country not in map_data:
            map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
            
        map_data[country]["total_users"] += c
        
        if province not in map_data[country]["provinces"]:
            map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
            
        map_data[country]["provinces"][province]["users"] += c

    for row in res_inv.all():
        country = str(row[0]).strip().upper() if row[0] else "Desconocido"
        province = str(row[1]).strip() if row[1] else "Desconocida"
        c = int(row[2]) if row[2] else 0
        
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