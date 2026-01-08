import streamlit as st
import hashlib
import re
import random
from urllib.parse import quote

# --- VALIDACIONES ---
def validar_formato_telefono(phone):
    if not phone: return False
    return bool(re.match(r'^\d{7,15}$', phone))

def limpiar_telefono(phone):
    if not phone: return ""
    return re.sub(r'\D', '', phone)

# --- CRIPTOGRAFÍA SEGURA (ANTI-ERROR) ---
def encrypt_phone(phone):
    key = 12345 
    try:
        clean = int(limpiar_telefono(phone))
        encrypted = clean ^ key
        return str(encrypted)
    except:
        return phone 

def decrypt_phone(encrypted_phone):
    """
    Si falla la desencriptación (porque el dato es viejo o texto),
    devuelve el dato original en lugar de romper la app.
    """
    key = 12345
    try:
        enc = int(encrypted_phone)
        decrypted = enc ^ key
        return str(decrypted)
    except:
        # Si da error, devolvemos el valor original (fallback)
        return str(encrypted_phone) if encrypted_phone else "No disponible"

# --- HASHING ---
def hash_phone_searchable(phone):
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def hash_password(password):
    clean_pass = str(password).strip()
    return hashlib.sha256(clean_pass.encode()).hexdigest()

def check_password(plain_password, hashed_password):
    return hash_password(plain_password) == hashed_password

# --- UI ---
def spinner_futbolero():
    msgs = ["Calentando motores...", "Revisando el VAR...", "Inflando las pelotas..."]
    return st.spinner(random.choice(msgs))

# --- WHATSAPP ---
def generar_link_whatsapp_wishlist(wishlist_ids):
    if not wishlist_ids: return None
    lista_str = ", ".join(map(str, wishlist_ids))
    app_url = "https://figus26.streamlit.app" 
    texto = f"¡Hola! 👋 Me faltan estas figus del Mundial 2026:\n\n{lista_str}\n\nSi tenés alguna, avisame! 🙏\n\n_Gestionado por Figus26_\n¡Sumate y cambiá las tuyas! ⚽ 👉 {app_url}"
    return f"https://wa.me/?text={quote(texto)}"