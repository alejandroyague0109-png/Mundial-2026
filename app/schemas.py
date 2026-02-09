from pydantic import BaseModel
from typing import Optional

# Esto define qué esperamos recibir del formulario de login
class UserLogin(BaseModel):
    phone: str
    password: str

# Esto define qué datos mostramos del usuario (para no mostrar la password por error)
class UserShow(BaseModel):
    id: int
    nick: str
    province: str
    is_premium: bool
    
    class Config:
        from_attributes = True