import os
import re
import hashlib
import httpx # Librería asíncrona para peticiones HTTP
from urllib.parse import quote
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE SEGURIDAD (BCRYPT) ---
# Inicializamos el contexto de encriptación profesional
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- VALIDACIONES ---
def validar_formato_telefono(phone: str) -> bool:
    if not phone: return False
    return bool(re.match(r'^\d{7,15}$', phone))

def limpiar_telefono(phone: str) -> str:
    """Deja solo los números del teléfono."""
    if not phone: return ""
    return re.sub(r'\D', '', str(phone))

# --- CRIPTOGRAFÍA & HASHING ---

def hash_phone_searchable(phone: str) -> str:
    """
    Hash SHA256 del teléfono. 
    Sirve para buscar usuarios en la base de datos sin guardar el número real 
    en texto plano (índice de privacidad).
    """
    clean = limpiar_telefono(phone)
    return hashlib.sha256(clean.encode()).hexdigest()

def hash_password(password: str) -> str:
    """
    Genera un hash seguro con sal (Bcrypt).
    Reemplaza la lógica antigua de SHA256 simple.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña plana coincide con el hash.
    NOTA: Renombrado de 'check_password' a 'verify_password' para compatibilidad.
    """
    return pwd_context.verify(plain_password, hashed_password)

def encrypt_phone(phone: str) -> str:
    """
    Ofuscación visual simple (XOR) para el Frontend.
    No usar para seguridad crítica, solo para ocultar el número en la UI.
    """
    key = 12345 
    try:
        clean = int(limpiar_telefono(phone))
        encrypted = clean ^ key
        return str(encrypted)
    except:
        return ""

def decrypt_phone(encrypted_phone: str) -> str:
    """Desencriptación XOR."""
    key = 12345
    try:
        enc = int(encrypted_phone)
        decrypted = enc ^ key
        return str(decrypted)
    except:
        return ""

# --- NOTIFICACIONES ASÍNCRONAS (TELEGRAM) ---
async def enviar_telegram_async(matches_dict: dict, uploader_nick: str):
    """
    Envía alertas a Telegram de forma asíncrona (no bloquea la app).
    """
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        return

    base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async with httpx.AsyncClient() as client:
        for chat_id, figus_encontradas in matches_dict.items():
            try:
                figus_str = ", ".join(map(str, figus_encontradas))
                texto = (
                    f"🔔 **¡Alerta de Mercado!**\n\n"
                    f"El usuario *{uploader_nick}* acaba de publicar figuritas que buscabas:\n"
                    f"🔥 **#{figus_str}**\n\n"
                    f"Entrá ya a la app para ofertar."
                )
                await client.post(base_url, data={
                    "chat_id": chat_id, 
                    "text": texto, 
                    "parse_mode": "Markdown"
                })
            except Exception as e:
                print(f"Error enviando notificación Telegram a {chat_id}: {e}")

# --- UTILIDADES DE PARSEO (Para Carga de Figus) ---

def parse_smart_input(text: str, start_index_global: int, count_items: int) -> set[int]:
    """
    Convierte inputs del usuario (Ej: "1, 2, 5-10") a IDs globales de la DB.
    """
    if not text:
        return set()

    result_global_ids = set()
    clean_text = re.sub(r'[^\d\-]+', ',', text)
    parts = clean_text.split(',')
    
    min_local = 1
    max_local = count_items

    for part in parts:
        part = part.strip()
        if not part: continue
            
        if '-' in part:
            try:
                s_str, e_str = part.split('-')
                if not s_str or not e_str: continue
                s, e = int(s_str), int(e_str)
                if s > e: s, e = e, s
                
                for local_num in range(s, e + 1):
                    if min_local <= local_num <= max_local:
                        global_id = start_index_global + local_num - 1
                        result_global_ids.add(global_id)
            except ValueError: continue
        else:
            try:
                local_num = int(part)
                if min_local <= local_num <= max_local:
                    global_id = start_index_global + local_num - 1
                    result_global_ids.add(global_id)
            except ValueError: continue
                
    return result_global_ids

def generar_link_whatsapp(phone: str, mensaje: str = "") -> str:
    """Genera un link directo a WhatsApp API."""
    clean_phone = limpiar_telefono(phone)
    if not clean_phone: return "#"
    
    base = f"https://wa.me/{clean_phone}"
    if mensaje:
        encoded_msg = quote(mensaje)
        base += f"?text={encoded_msg}"
    
    return base