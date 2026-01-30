import streamlit as st
import threading
import requests
import config 
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

# --- PARSER INTELIGENTE (CARGA MASIVA) ---
def parse_smart_input(text_input, page_start_id, page_end_id):
    """
    Convierte texto tipo '1, 2, 5-8' en una lista de IDs absolutos reales.
    Ejemplo: Si page_start_id es 20 (Brasil) y el usuario escribe '1', devuelve [20].
    """
    if not text_input: return []
    
    # 1. Normalizar separadores (cambiar saltos de línea y comas por espacios)
    normalized = re.sub(r'[,\n;]', ' ', text_input)
    parts = normalized.split()
    
    result_ids = set()
    offset = page_start_id - 1 # Si la pág empieza en 20, el '1' es 20. O sea 1 + 19.
    
    for part in parts:
        part = part.strip()
        if not part: continue
        
        try:
            # Caso Rango: "5-10"
            if '-' in part:
                start, end = part.split('-')
                s = int(start)
                e = int(end)
                # Validar orden
                if s > e: s, e = e, s
                
                # Generar rango y aplicar offset
                for num in range(s, e + 1):
                    abs_id = num + offset
                    if page_start_id <= abs_id <= page_end_id:
                        result_ids.add(abs_id)
            
            # Caso Número Único: "5"
            else:
                num = int(part)
                abs_id = num + offset
                if page_start_id <= abs_id <= page_end_id:
                    result_ids.add(abs_id)
                    
        except ValueError:
            continue # Si escribe basura ("hola"), se ignora.

    return list(result_ids)

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

# --- WHATSAPP (COMPARTIR COMPLETO) ---
def generar_link_compartir_completo(wishlist_ids, repes_ids):
    """Genera un link de WhatsApp con Faltantes y Repetidas."""
    if not wishlist_ids and not repes_ids:
        return None
    
    # LINK DE LA APP
    app_url = "https://figus26.streamlit.app" 
    
    # Encabezado
    texto = "🏆 *Figus 26 - Mi Álbum*\n\n"
    
    # Sección Faltantes
    if wishlist_ids:
        lista_wish = ", ".join(map(str, wishlist_ids))
        texto += f"❌ *Me Faltan:*\n{lista_wish}\n\n"
    else:
        texto += "❌ *Me Faltan:* ¡Llené todo! (o no cargué nada 😅)\n\n"
        
    # Sección Repetidas
    if repes_ids:
        lista_repes = ", ".join(map(str, repes_ids))
        texto += f"✅ *Tengo Repes:*\n{lista_repes}\n\n"
    else:
        texto += "✅ *Tengo Repes:* Ninguna por ahora.\n\n"
    
    # Footer
    texto += f"📲 *Cambiemos acá:* {app_url}"
    
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

# --- NOTIFICACIONES ASÍNCRONAS (TELEGRAM) ---
# AGREGADO: Esta función faltaba y es requerida por database.py
def _enviar_telegram_async(matches_dict, uploader_nick):
    """
    Función interna que se ejecuta en segundo plano.
    Envía mensajes a los usuarios Premium que tenían en Wishlist lo que se acaba de cargar.
    """
    token = getattr(config, 'TELEGRAM_BOT_TOKEN', None)
    if not token or token == "TOKEN_NO_CONFIGURADO":
        return

    base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    for chat_id, figus_encontradas in matches_dict.items():
        try:
            figus_str = ", ".join(map(str, figus_encontradas))
            texto = (
                f"🔔 **¡Alerta de Mercado!**\n\n"
                f"El usuario *{uploader_nick}* acaba de publicar figuritas que buscabas:\n"
                f"🔥 **#{figus_str}**\n\n"
                f"Entrá ya a la app para ofertar."
            )
            requests.post(base_url, data={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Error enviando notificación: {e}")

def disparar_notificaciones_thread(matches_dict, uploader_nick):
    """
    Lanza el proceso de notificaciones en un hilo separado para no bloquear la UI.
    """
    if not matches_dict:
        return
    
    # Creamos y arrancamos el hilo
    thread = threading.Thread(target=_enviar_telegram_async, args=(matches_dict, uploader_nick))
    thread.start()