import re
import hashlib
import bcrypt
import streamlit as st
from cryptography.fernet import Fernet

# --- CRIPTOGRAFÍA DE DATOS (TELÉFONOS) ---

def get_fernet():
    """Inicializa el motor de encriptación con la clave de los Secrets."""
    try:
        # Asegúrate de tener ENCRYPTION_KEY en .streamlit/secrets.toml
        key = st.secrets["ENCRYPTION_KEY"]
        return Fernet(key.encode())
    except Exception:
        # Si falla (ej: local sin secrets), devolvemos None para no romper todo, 
        # pero la seguridad estará comprometida.
        return None

def hash_phone_searchable(phone):
    """
    Crea un Hash SHA-256 del teléfono. 
    Sirve para BUSCAR usuarios (Login/Registro) sin guardar el número real.
    Es unidireccional (No se puede volver al número original).
    """
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def encrypt_phone(phone):
    """
    Encripta el teléfono para guardarlo en la DB. 
    Solo se puede leer usando la clave secreta (bidireccional).
    """
    f = get_fernet()
    if f:
        clean = limpiar_telefono(phone)
        return f.encrypt(clean.encode()).decode()
    return None

def decrypt_phone(encrypted_phone):
    """
    Recupera el teléfono original para mostrarlo en el botón de WhatsApp.
    """
    f = get_fernet()
    if f and encrypted_phone:
        try:
            return f.decrypt(encrypted_phone.encode()).decode()
        except:
            return None
    return None

# --- FORMATO Y LIMPIEZA ---

def validar_formato_telefono(phone):
    """Valida que parezca un teléfono argentino."""
    # Acepta con o sin +54, con o sin 9, etc.
    patron = r'^(\+?54)?(9)?\d{10}$'
    return bool(re.match(patron, str(phone)))

def limpiar_telefono(phone):
    """Deja solo los números."""
    return re.sub(r'\D', '', str(phone))

# --- SEGURIDAD DE CONTRASEÑAS ---

def hash_password(password):
    """Convierte la contraseña en un hash seguro con sal (bcrypt)."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Verifica si la contraseña coincide con el hash guardado."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False