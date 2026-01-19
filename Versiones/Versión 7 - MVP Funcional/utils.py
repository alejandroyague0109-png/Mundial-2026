import streamlit as st
import hashlib
import re
import random
from urllib.parse import quote

# --- VALIDACIONES ---
def validar_formato_telefono(phone):
    """Valida que el teléfono tenga entre 7 y 15 dígitos numéricos."""
    if not phone: return False
    return bool(re.match(r'^\d{7,15}$', phone))

def limpiar_telefono(phone):
    """Elimina espacios, guiones y símbolos no numéricos."""
    if not phone: return ""
    return re.sub(r'\D', '', phone)

# --- CRIPTOGRAFÍA SIMPLE (PARA DATOS SENSIBLES) ---
def encrypt_phone(phone):
    """
    Simulación de encriptación reversible (XOR simple) para la demo.
    Nota: En producción real, usar criptografía asimétrica o Fernet.
    """
    key = 12345 # Clave simple para el MVP
    try:
        clean = int(limpiar_telefono(phone))
        encrypted = clean ^ key
        return str(encrypted)
    except:
        return None

def decrypt_phone(encrypted_phone):
    key = 12345
    try:
        enc = int(encrypted_phone)
        decrypted = enc ^ key
        return str(decrypted)
    except:
        return None

# --- HASHING (CONTRASEÑAS Y BÚSQUEDAS) ---
def hash_phone_searchable(phone):
    """Hash SHA256 para búsquedas exactas (login/registro)."""
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def hash_password(password):
    """Hash SHA256 para contraseñas. Incluye .strip() para evitar errores por espacios."""
    # Convertimos a string y quitamos espacios al inicio/final por seguridad
    clean_pass = str(password).strip()
    return hashlib.sha256(clean_pass.encode()).hexdigest()

def check_password(plain_password, hashed_password):
    """Verifica si la contraseña ingresada coincide con la guardada."""
    return hash_password(plain_password) == hashed_password

# --- UI / UX ---
def spinner_futbolero():
    """Genera un spinner con mensaje aleatorio."""
    msgs = [
        "Calentando motores...", 
        "Atándose los botines...", 
        "Revisando el VAR...", 
        "Inflando las pelotas...", 
        "Cortando el pasto...",
        "Charlando con el árbitro..."
    ]
    return st.spinner(random.choice(msgs))

# --- WHATSAPP ---
def generar_link_whatsapp_wishlist(wishlist_ids):
    if not wishlist_ids:
        return None
    
    # Agrupamos los números
    lista_str = ", ".join(map(str, wishlist_ids))
    
    # LINK DE LA APP (Ajustalo cuando tengas el deploy final)
    app_url = "https://figus26.streamlit.app" 
    
    texto = f"¡Hola! 👋 Me faltan estas figus del Mundial 2026:\n\n{lista_str}\n\nSi tenés alguna, avisame! 🙏\n\n_Gestionado por Figus26_\n¡Sumate y cambiá las tuyas! ⚽ 👉 {app_url}"
    
    return f"https://wa.me/?text={quote(texto)}"

# --- GESTIÓN DE SESIÓN (PERSISTENCIA) ---
def crear_token_sesion(user_id):
    """Crea un token seguro: ID + Hash"""
    salt = "FIGUS_MENDOZA_2026"
    hash_val = hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()
    return f"{user_id}::{hash_val}"

def validar_token_sesion(token):
    """Verifica si el token de la URL es válido."""
    try:
        if not token or "::" not in token: return None
        user_id, hash_recibido = token.split("::")
        
        salt = "FIGUS_MENDOZA_2026"
        hash_real = hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()
        
        if hash_recibido == hash_real:
            return int(user_id)
        return None
    except:
        return None