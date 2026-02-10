# app/dependencies.py
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Recupera el usuario actual basándose en la cookie 'user_id'.
    Si no hay cookie o el usuario no existe, lanza error 401.
    """
    user_id_cookie = request.cookies.get("user_id")
    
    if not user_id_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No has iniciado sesión"
        )
    
    try:
        user_id = int(user_id_cookie)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
            
        return user
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID de usuario inválido"
        )