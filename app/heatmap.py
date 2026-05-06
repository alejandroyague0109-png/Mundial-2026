# app/routers/heatmap.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pathlib import Path
import traceback

from app.database import get_db

router = APIRouter(tags=["Heatmap"])
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/heatmap")
async def view_heatmap(request: Request, debug: bool = False, db: AsyncSession = Depends(get_db)):
    debug_info = {}

    # 1. Usuarios
    try:
        res_users = await db.execute(text("""
            SELECT country_code, province, COUNT(id) 
            FROM users 
            GROUP BY country_code, province
        """))
        users_rows = res_users.all()
        debug_info["1_query_usuarios"] = "OK"
        debug_info["2_usuarios_encontrados"] = len(users_rows)
        debug_info["3_ejemplo_usuarios"] = [str(r) for r in users_rows[:3]] if users_rows else []
    except Exception as e:
        debug_info["1_query_usuarios"] = "ERROR"
        debug_info["error_detalle_usuarios"] = str(e)
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
        debug_info["4_query_figuritas"] = "OK"
        debug_info["5_figuritas_encontradas"] = len(inv_rows)
        debug_info["6_ejemplo_figuritas"] = [str(r) for r in inv_rows[:3]] if inv_rows else []
    except Exception as e:
        debug_info["4_query_figuritas"] = "ERROR"
        debug_info["error_detalle_figuritas"] = str(e)
        inv_rows = []

    # 3. Armado del diccionario
    map_data = {}
    try:
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

        debug_info["7_paises_procesados"] = list(map_data.keys())
        if "AR" in map_data:
            debug_info["8_datos_argentina"] = map_data["AR"]
            
    except Exception as e:
        debug_info["error_procesamiento"] = str(e)
        debug_info["traceback"] = traceback.format_exc()

    # MODO DEBUG ACTIVO: Si entramos con ?debug=true, vemos los datos crudos
    if debug:
        return JSONResponse(content=debug_info)

    # Si no hay debug, mostramos el mapa normal
    return templates.TemplateResponse("heatmap.html", {
        "request": request,
        "map_data": map_data
    })