import re
import hashlib
import bcrypt
import streamlit as st
import random # <--- Necesario para elegir frases al azar
from cryptography.fernet import Fernet
from contextlib import contextmanager

# --- FEEDBACK VISUAL (SPINNER FUTBOLERO) ---
@contextmanager
def spinner_futbolero():
    """Muestra un mensaje de carga aleatorio con temática de fútbol/figuritas."""
    frases = [
        "⚽ Abriendo paquete...",
        "🔎 Buscando la difícil...",
        "🔄 Mezclando el mazo...",
        "📞 Llamando al VAR...",
        "🧤 Calentando los guantes...",
        "🏟️ Cortando el pasto...",
        "📝 Anotando en la planilla...",
        "🏃‍♂️ Saliendo de contra..."
    ]
    mensaje = random.choice(frases)
    with st.spinner(mensaje):
        yield

# --- CRIPTOGRAFÍA DE DATOS ---
def get_fernet():
    try:
        key = st.secrets["ENCRYPTION_KEY"]
        return Fernet(key.encode())
    except Exception:
        return None

def hash_phone_searchable(phone):
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def encrypt_phone(phone):
    f = get_fernet()
    if f:
        clean = limpiar_telefono(phone)
        return f.encrypt(clean.encode()).decode()
    return None

def decrypt_phone(encrypted_phone):
    f = get_fernet()
    if f and encrypted_phone:
        try:
            return f.decrypt(encrypted_phone.encode()).decode()
        except:
            return None
    return None

# --- FORMATO Y LIMPIEZA ---
def validar_formato_telefono(phone):
    patron = r'^(\+?54)?(9)?\d{10}$'
    return bool(re.match(patron, str(phone)))

def limpiar_telefono(phone):
    return re.sub(r'\D', '', str(phone))

# --- SEGURIDAD DE CONTRASEÑAS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False