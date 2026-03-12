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
from app.locations import LOCATIONS_BY_COUNTRY

router = APIRouter(tags=["Safe Spots"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- NUEVO: Inyectamos el traductor globalmente al HTML ---
from app.translations import t
templates.env.globals["t"] = t
# ----------------------------------------------------------

# 1. RUTA PRINCIPAL (PÚBLICA Y ADAPTATIVA)
@router.get("/safe-spots", response_class=HTMLResponse)
async def view_safe_spots(
    request: Request, 
    provincia: str = None, 
    zona: str = None, 
    db: AsyncSession = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    user = None
    
    # 1. Intentamos buscar al usuario si tiene cookie
    if user_id: 
        result_user = await db.execute(select(User).where(User.id == int(user_id)))
        user = result_user.scalars().first()

    # Extraemos las categorías únicas
    cat_result = await db.execute(select(PuntoSeguro.categoria).distinct())
    categorias = [c for c in cat_result.scalars().all() if c]

    # 2. Lógica de asignación de zona con las 3 prioridades
    
    # 2. Lógica de asignación de zona con las 3 prioridades
    
    # Prioridad 1: Viene por la URL (desde WhatsApp u otro link)
    if provincia and zona:
        default_country = "AR" # Fallback temporal si viene de un link viejo
        default_province = provincia
        default_zone = zona
    
    # Prioridad 2: Está logueado y tiene su zona
    elif user and user.province and user.zone:
        default_country = user.country_code
        default_province = user.province
        default_zone = user.zone
        
    # Prioridad 3: Curioso sin login. Dejamos Argentina por defecto
    else:
        default_country = "AR"
        default_province = ""
        default_zone = ""

    return templates.TemplateResponse("safe_spots.html", {
        "request": request,
        "user": user,  
        "active_tab": "safe_spots",
        "album_structure": ALBUM_STRUCTURE,
        "locations_json": json.dumps(LOCATIONS_BY_COUNTRY), # <-- Pasamos todo LATAM
        "categorias": categorias,
        "default_country": default_country, # <-- NUEVO
        "default_prov": default_province,
        "default_zone": default_zone
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