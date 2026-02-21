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
        "locations": ARGENTINA,  # <--- CORRECCIÓN AQUÍ (Para los modales)
        "locations_json": json.dumps(ARGENTINA), # Para el Javascript
        "categorias": categorias
    })

# 2. API DE BÚSQUEDA
@router.get("/safe-spots/search")
async def search_safe_spots(
    request: Request,
    provincia: str = "",
    localidad: str = "",
    categoria: str = "",
    db: AsyncSession = Depends(get_db)
):
    stmt = select(PuntoSeguro)
    
    # Aplicar filtros
    if provincia and provincia != "None":
        stmt = stmt.where(PuntoSeguro.provincia == provincia)
        
    if localidad and localidad != "None":
        stmt = stmt.where(PuntoSeguro.departamento == localidad)
        
    if categoria and categoria != "None":
        stmt = stmt.where(PuntoSeguro.categoria == categoria)
        
    # --- LA MAGIA ESTÁ AQUÍ ---
    # Ordenamos para que los verificados (True) vengan siempre primero
    stmt = stmt.order_by(PuntoSeguro.verificado.desc())
    # --------------------------

    result = await db.execute(stmt)
    spots = result.scalars().all()
    
    # --- FILTRO TEMPORAL: Máximo 3 en total por búsqueda ---
    spots_filtrados = []
    categorias_vistas = set()
    
    # 1. Priorizamos buscar 3 locales de categorías distintas
    for s in spots:
        if len(spots_filtrados) >= 3:
            break
        if s.categoria not in categorias_vistas:
            spots_filtrados.append(s)
            categorias_vistas.add(s.categoria)
            
    # 2. Si no juntamos 3 (ej: porque todos en el pueblo son "kiosco"), 
    # rellenamos con los restantes hasta llegar a 3.
    for s in spots:
        if len(spots_filtrados) >= 3:
            break
        if s not in spots_filtrados:
            spots_filtrados.append(s)
    # -------------------------------------------------------
    
    # Formatear la respuesta usando la lista filtrada
    spots_data = []
    for s in spots_filtrados:
        spots_data.append({
            "id": str(s.id),
            "nombre": s.nombre,
            "categoria": s.categoria,
            "provincia": s.provincia,
            "departamento": s.departamento,
            "latitud": s.latitud,
            "longitud": s.longitud,
            "verificado": s.verificado
        })
        
    return JSONResponse(content={"spots": spots_data})