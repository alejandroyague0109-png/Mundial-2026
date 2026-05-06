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
    map_data = {}
    
    try:
        # 1. Usuarios con SQL Crudo (El que sabemos que funciona)
        res_users = await db.execute(text("""
            SELECT country_code, province, COUNT(id) 
            FROM users 
            GROUP BY country_code, province
        """))
        
        for row in res_users.all():
            country = str(row[0]).strip().upper() if row[0] else "AR"
            province = str(row[1]).strip() if row[1] else "Desconocida"
            count = int(row[2]) if row[2] else 0
            
            if country not in map_data:
                map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
                
            map_data[country]["total_users"] += count
            
            if province not in map_data[country]["provinces"]:
                map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
                
            map_data[country]["provinces"][province]["users"] += count
    except Exception as e:
        print("Error Usuarios:", e)

    try:
        # 2. Figuritas con SQL Crudo
        res_inv = await db.execute(text("""
            SELECT u.country_code, u.province, COUNT(i.id) 
            FROM inventory i 
            JOIN users u ON i.user_id = u.id 
            GROUP BY u.country_code, u.province
        """))
        
        for row in res_inv.all():
            country = str(row[0]).strip().upper() if row[0] else "AR"
            province = str(row[1]).strip() if row[1] else "Desconocida"
            count = int(row[2]) if row[2] else 0
            
            if country not in map_data:
                map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
                
            map_data[country]["total_activity"] += count
            
            if province not in map_data[country]["provinces"]:
                map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
                
            map_data[country]["provinces"][province]["activity"] += count
    except Exception as e:
        print("Error Figuritas:", e)

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })