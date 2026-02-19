import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.database import get_db
from app.models import User, PuntoSeguro
from app.data_album import ALBUM_STRUCTURE
from app.locations import ARGENTINA

router = APIRouter(tags=["Safe Spots"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 1. RUTA PRINCIPAL (Renderiza el HTML)
@router.get("/safe-spots", response_class=HTMLResponse)
async def view_safe_spots(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id: 
        return RedirectResponse(url="/login", status_code=303)

    result_user = await db.execute(select(User).where(User.id == int(user_id)))
    user = result_user.scalars().first()
    if not user: 
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("user_id")
        return response

    # Extraemos las categorías únicas de la DB para armar el filtro dinámicamente
    cat_result = await db.execute(select(PuntoSeguro.categoria).distinct())
    categorias = [c for c in cat_result.scalars().all() if c]

    return templates.TemplateResponse("safe_spots.html", {
        "request": request,
        "user": user,
        "active_tab": "safe_spots",
        "album_structure": ALBUM_STRUCTURE,
        "locations_json": json.dumps(ARGENTINA), # Para el Javascript de los filtros
        "categorias": categorias
    })

# 2. API DE BÚSQUEDA (El Javascript consulta aquí al cambiar los filtros)
@router.get("/safe-spots/search")
async def search_safe_spots(
    request: Request,
    provincia: str = "",
    localidad: str = "",
    categoria: str = "",
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PuntoSeguro)
    
    # Aplicar filtros solo si el usuario seleccionó algo
    if provincia:
        stmt = stmt.where(PuntoSeguro.provincia == provincia)
    if localidad:
        stmt = stmt.where(PuntoSeguro.departamento == localidad)
    if categoria:
        stmt = stmt.where(PuntoSeguro.categoria == categoria)
        
    result = await db.execute(stmt)
    spots = result.scalars().all()
    
    # Formatear la respuesta
    spots_data = []
    for s in spots:
        spots_data.append({
            "id": s.id,
            "nombre": s.nombre,
            "categoria": s.categoria,
            "provincia": s.provincia,
            "departamento": s.departamento,
            "latitud": s.latitud,
            "longitud": s.longitud,
            "verificado": s.verificado
        })
        
    return JSONResponse(content={"spots": spots_data})