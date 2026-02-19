from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.database import get_db
from app.models import User

router = APIRouter(tags=["Safe Spots"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/safe-spots", response_class=HTMLResponse)
async def view_safe_spots(request: Request, db: AsyncSession = Depends(get_db)):
    # 1. Validar que el usuario esté logueado (misma lógica que album.py)
    user_id = request.cookies.get("user_id")
    if not user_id: 
        return RedirectResponse(url="/login", status_code=303)

    result_user = await db.execute(select(User).where(User.id == int(user_id)))
    user = result_user.scalars().first()
    
    if not user: 
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("user_id")
        return response

    # 2. Renderizar la nueva plantilla
    # Pasamos active_tab para que el layout sepa en qué pestaña estamos
    return templates.TemplateResponse("safe_spots.html", {
        "request": request,
        "user": user,
        "active_tab": "safe_spots"
    })