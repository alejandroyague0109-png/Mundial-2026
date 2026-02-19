from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nick = Column(String, unique=True, index=True)
    phone_hash = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    
    # Datos de Ubicación
    province = Column(String)
    zone = Column(String)

    # --- CAMPOS DE SEGURIDAD ---
    secret_question = Column(String, nullable=True)
    secret_answer = Column(String, nullable=True)

    # Datos de Perfil / Sistema
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    reputation = Column(Integer, default=0)
    
    # --- SISTEMA DE CRÉDITOS DIARIOS ---
    daily_contacts_count = Column(Integer, default=0)
    last_contact_date = Column(Date, nullable=True)
    # -----------------------------------

    telegram_chat_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación: Un usuario tiene muchos items en el inventario
    inventory_items = relationship("Inventory", back_populates="owner")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Clave foránea
    sticker_num = Column(Integer, index=True)
    status = Column(String) # 'tengo', 'wishlist', 'repetida'
    quantity = Column(Integer, default=1)
    price = Column(Integer, default=0)

    # Relación: Un item pertenece a un usuario
    owner = relationship("User", back_populates="inventory_items")

# --- CLASE PARA GESTIONAR TRANSACCIONES/PENDIENTES ---
class ContactLog(Base):
    __tablename__ = "contact_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))     # Quien inició el contacto (Interesado)
    target_id = Column(Integer, ForeignKey("users.id"))   # A quien contactó (Dueño)
    
    # Nuevos campos necesarios para la pestaña Pendientes
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=True) # La figurita específica
    status = Column(String, default="pending") # Estados: 'pending', 'completed', 'cancelled'
    rating = Column(Integer, nullable=True)    # 1 (Positivo) o 0/Null (Neutro/Sin calificar)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones para facilitar consultas
    initiator = relationship("User", foreign_keys=[user_id])
    target = relationship("User", foreign_keys=[target_id])
    item = relationship("Inventory")

# --- NUEVA CLASE: PUNTOS SEGUROS ---
class PuntoSeguro(Base):
    __tablename__ = "puntos_seguros"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String)
    categoria = Column(String)
    provincia = Column(String)
    departamento = Column(String)
    distrito = Column(String, nullable=True)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    latitud = Column(Float)
    longitud = Column(Float)
    verificado = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=True)
    telefono_wa = Column(String, nullable=True)
    estado_limpieza = Column(String, nullable=True)