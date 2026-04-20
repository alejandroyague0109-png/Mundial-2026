from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime
import pytz

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nick = Column(String, unique=True, index=True)
    phone_hash = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    
    # Datos de Ubicación
    country_code = Column(String(2), default="AR", nullable=False)
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

    @property
    def effective_daily_contacts(self):
        # Si es Premium, no nos importa el contador, siempre tiene "0" de límite o no aplica.
        if self.is_premium:
            return 0 
            
        # Si nunca hizo un contacto
        if not self.last_contact_date:
            return 0
            
        # Configuramos la hora de Argentina para que se resetee a la medianoche local
        tz_ar = pytz.timezone('America/Argentina/Buenos_Aires')
        hoy = datetime.now(tz_ar).date()
        
        # Si la última vez que contactó fue HOY, mostramos el contador real
        if self.last_contact_date == hoy:
            return self.daily_contacts_count
        else:
            # Si fue ayer o antes, el contador virtual es 0 (¡Magia!)
            return 0

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Clave foránea
    sticker_num = Column(Integer, index=True)

    country_code = Column(String(2), default="AR", nullable=False)

    status = Column(String) # 'tengo', 'wishlist', 'repetida'
    quantity = Column(Integer, default=1)
    price = Column(Integer, default=0)

    # Relación: Un item pertenece a un usuario
    owner = relationship("User", back_populates="inventory_items")
    # --- LA NUEVA COLUMNA ---
    is_special = Column(Boolean, nullable=False, default=False)

# --- CLASE PARA GESTIONAR TRANSACCIONES/PENDIENTES ---
class ContactLog(Base):
    __tablename__ = "contact_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))     # Quien inició el contacto (Interesado)
    target_id = Column(Integer, ForeignKey("users.id"))   # A quien contactó (Dueño)
    
    country_code = Column(String(2), default="AR", nullable=False)    

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

    country_code = Column(String(2), default="AR", nullable=False)

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