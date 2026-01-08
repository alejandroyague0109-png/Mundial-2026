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
    """Elimina espacios, guiones y símbolos no numéricos para guardar limpio."""
    if not phone: return ""
    return re.sub(r'\D', '', phone)

# --- CRIPTOGRAFÍA SIMPLE (XOR) ---
# Nota: Esto es seguridad básica para el MVP.
def encrypt_phone(phone):
    key = 12345 
    try:
        clean = int(limpiar_telefono(phone))
        encrypted = clean ^ key
        return str(encrypted)
    except:
        return phone # Si falla, guardamos el original

def decrypt_phone(encrypted_phone):
    """
    Desencripta el teléfono. 
    CORRECCIÓN: Si el dato no es un número encriptado (ej: datos viejos), 
    devuelve el dato tal cual para evitar errores de pantalla roja.
    """
    key = 12345
    try:
        # Intentamos convertir a entero para desencriptar
        enc = int(encrypted_phone)
        decrypted = enc ^ key
        return str(decrypted)
    except:
        # Si falla (porque es None o texto plano), devolvemos lo que llegó
        return str(encrypted_phone) if encrypted_phone else "No disponible"

# --- HASHING (SEGURIDAD) ---
def hash_phone_searchable(phone):
    """Hash para buscar usuarios (Login/Registro)."""
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def hash_password(password):
    """Hash de contraseña. Usamos .strip() para evitar errores por espacios invisibles."""
    clean_pass = str(password).strip()
    return hashlib.sha256(clean_pass.encode()).hexdigest()

def check_password(plain_password, hashed_password):
    return hash_password(plain_password) == hashed_password

# --- UI / UX ---
def spinner_futbolero():
    """Genera un spinner con mensaje aleatorio para la espera."""
    msgs = [
        "Calentando motores...", 
        "Atándose los botines...", 
        "Revisando el VAR...", 
        "Inflando las pelotas...", 
        "Cortando el pasto...",
        "Charlando con el árbitro...",
        "Preparando el mate..."
    ]
    return st.spinner(random.choice(msgs))

# --- WHATSAPP HELPER ---
def generar_link_whatsapp_wishlist(wishlist_ids):
    """Genera el link para compartir faltantes."""
    if not wishlist_ids:
        return None
    
    # Agrupamos los números
    lista_str = ", ".join(map(str, wishlist_ids))
    
    # LINK DE LA APP
    app_url = "https://figus26.streamlit.app" 
    
    texto = f"¡Hola! 👋 Me faltan estas figus del Mundial 2026:\n\n{lista_str}\n\nSi tenés alguna, avisame! 🙏\n\n_Gestionado por Figus26_\n¡Sumate y cambiá las tuyas! ⚽ 👉 {app_url}"
    
    return f"https://wa.me/?text={quote(texto)}"