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
    print("\n" + "="*40)
    print("🚀 INICIANDO DEBUG DE HEATMAP 🚀")
    
    # 1. Usuarios
    try:
        res_users = await db.execute(text("""
            SELECT country_code, province, COUNT(id) 
            FROM users 
            GROUP BY country_code, province
        """))
        users_rows = res_users.all()
        print(f"[✅] QUERY USUARIOS: Trajo {len(users_rows)} filas.")
        if users_rows:
            print(f"    Ejemplo de fila 1: {users_rows[0]}")
    except Exception as e:
        print(f"[❌] ERROR QUERY USUARIOS: {e}")
        users_rows = []

    # 2. Figuritas
    try:
        res_inv = await db.execute(text("""
            SELECT u.country_code, u.province, COUNT(i.id) 
            FROM inventory i 
            JOIN users u ON i.user_id = u.id 
            GROUP BY u.country_code, u.province
        """))
        inv_rows = res_inv.all()
        print(f"[✅] QUERY FIGURITAS: Trajo {len(inv_rows)} filas.")
        if inv_rows:
            print(f"    Ejemplo de fila 1: {inv_rows[0]}")
    except Exception as e:
        print(f"[❌] ERROR QUERY FIGURITAS: {e}")
        inv_rows = []

    map_data = {}

    # Procesar Usuarios
    for row in users_rows:
        country = str(row[0]).strip().upper() if row[0] else None
        province = str(row[1]).strip() if row[1] else "Desconocida"
        count = int(row[2]) if row[2] else 0
        
        if not country: continue
        
        if country not in map_data:
            map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
            
        map_data[country]["total_users"] += count
        
        if province not in map_data[country]["provinces"]:
            map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
            
        map_data[country]["provinces"][province]["users"] += count

    # Procesar Figuritas
    for row in inv_rows:
        country = str(row[0]).strip().upper() if row[0] else None
        province = str(row[1]).strip() if row[1] else "Desconocida"
        count = int(row[2]) if row[2] else 0
        
        if not country: continue
        
        if country not in map_data:
            map_data[country] = {"total_users": 0, "total_activity": 0, "provinces": {}}
            
        map_data[country]["total_activity"] += count
        
        if province not in map_data[country]["provinces"]:
            map_data[country]["provinces"][province] = {"users": 0, "activity": 0}
            
        map_data[country]["provinces"][province]["activity"] += count

    print(f"[✅] DICCIONARIO CREADO: {len(map_data.keys())} países encontrados.")
    if "AR" in map_data:
        print(f"    Datos de Argentina -> Usuarios: {map_data['AR']['total_users']} | Figuritas: {map_data['AR']['total_activity']}")
        provincias_ar = list(map_data['AR']['provinces'].keys())
        print(f"    Provincias AR encontradas: {len(provincias_ar)} {provincias_ar[:5]}...")
    
    print("="*40 + "\n")

    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })