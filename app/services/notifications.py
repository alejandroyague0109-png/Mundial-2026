# app/services/notifications.py
import os
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Inventory
import urllib.parse

# Configuración
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def notify_wishlist_match(db: AsyncSession, sticker_num: int, sticker_name: str, owner: User):
    """
    Busca usuarios Premium que tengan esta figurita en su Wishlist
    y les envía una alerta por Telegram.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ No hay Token de Telegram configurado.")
        return

   # 1. Buscar interesados (Premium + Wishlist + Tienen Telegram ID + MISMA ZONA)
    stmt = (
        select(User)
        .join(Inventory, User.id == Inventory.user_id)
        .where(
            Inventory.sticker_num == sticker_num,
            Inventory.status == 'wishlist',
            User.is_premium == True,
            User.telegram_chat_id.isnot(None),
            User.id != owner.id,     # No avisarse a uno mismo
            
            # --- FILTROS GEOGRÁFICOS (Optimizados en DB) ---
            User.province == owner.province,
            User.zone == owner.zone
            # -----------------------------------------------
        )
    )
    result = await db.execute(stmt)
    interested_users = result.scalars().all()

    if not interested_users:
        return

    # 2. Enviar mensajes (Asíncrono)
   async with httpx.AsyncClient() as client:
    for user in interested_users:
        
        # 1. GENERAR DEEP LINK (Codificamos los parámetros para evitar errores con espacios)
        safe_sticker = urllib.parse.quote(sticker_name)
        safe_nick = urllib.parse.quote(owner.nick)
        deep_link = f"https://canjealtoque26.com/market?sticker={safe_sticker}&nick={safe_nick}"

        # 2. CONSTRUCCIÓN DEL MENSAJE
        msg = (
            f"🚨 *¡APARECIÓ UNA DIFÍCIL!*\n\n"
            f"👤 *{owner.nick}* ({owner.province}) acaba de publicar:\n"
            f"🏆 *{sticker_name}*\n\n"
            f"🏃‍♂️ Corré al Mercado para contactarlo antes que te ganen.\n\n"
            f"📲 *Ver oferta:* {deep_link}"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": user.telegram_chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True 
        }
        
        try:
            # Enviamos y olvidamos
            await client.post(url, json=payload, timeout=5.0)
            print(f"✅ Notificación enviada a {user.nick}")
        except Exception as e:
            print(f"❌ Error enviando a {user.nick}: {e}")