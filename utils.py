import streamlit as st
import hashlib
import re
from urllib.parse import quote

def validar_formato_telefono(phone):
    """Valida que el teléfono tenga entre 7 y 15 dígitos numéricos."""
    if not phone: return False
    return bool(re.match(r'^\d{7,15}$', phone))

def limpiar_telefono(phone):
    """Elimina espacios, guiones y +."""
    if not phone: return ""
    return re.sub(r'\D', '', phone)

def encrypt_phone(phone):
    """
    Simulación de encriptación reversible (XOR simple) para la demo.
    En producción real, usar criptografía asimétrica o Fernet.
    """
    key = 12345 # Key simple para MVP
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

def hash_phone_searchable(phone):
    """Hash SHA256 para búsquedas exactas (login/registro)."""
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def hash_password(password):
    """Hash simple para contraseñas."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(plain_password, hashed_password):
    return hash_password(plain_password) == hashed_password

def spinner_futbolero():
    """Genera un spinner con mensaje aleatorio."""
    import random
    msgs = ["Calentando motores...", "Atándose los botines...", "Revisando el VAR...", "Inflando las pelotas...", "Cortando el pasto..."]
    return st.spinner(random.choice(msgs))

def generar_link_whatsapp_wishlist(wishlist_ids):
    if not wishlist_ids:
        return None
    
    # Agrupamos los números
    lista_str = ", ".join(map(str, wishlist_ids))
    
    # LINK DE LA APP (Ajustalo cuando tengas el deploy final)
    app_url = "https://figus26.streamlit.app" 
    
    texto = f"¡Hola! 👋 Me faltan estas figus del Mundial 2026:\n\n{lista_str}\n\nSi tenés alguna, avisame! 🙏\n\n_Gestionado por Figus26_\n¡Sumate y cambiá las tuyas! ⚽ 👉 {app_url}"
    
    return f"https://wa.me/?text={quote(texto)}"