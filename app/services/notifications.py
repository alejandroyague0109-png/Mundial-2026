# app/services/notifications.py
import os
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Inventory

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

    # 1. Buscar interesados (Premium + Wishlist + Tienen Telegram ID)
    stmt = (
        select(User)
        .join(Inventory, User.id == Inventory.user_id)
        .where(
            Inventory.sticker_num == sticker_num,
            Inventory.status == 'wishlist',
            User.is_premium == True,
            User.telegram_chat_id.isnot(None),
            User.id != owner.id  # No avisarse a uno mismo
        )
    )
    result = await db.execute(stmt)
    interested_users = result.scalars().all()

    if not interested_users:
        return

    # 2. Enviar mensajes (Asíncrono)
    async with httpx.AsyncClient() as client:
        for user in interested_users:
            # Construcción del mensaje profesional
            msg = (
                f"🚨 *¡APARECIÓ UNA DIFÍCIL!*\n\n"
                f"👤 *{owner.nick}* ({owner.province}) acaba de publicar:\n"
                f"🏆 *{sticker_name}*\n\n"
                f"🏃‍♂️ Corré al Mercado para contactarlo antes que te ganen.\n\n"
                f"📲 *Abrir App:* https://canjealtoque26.com"
            )
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": user.telegram_chat_id,
                "text": msg,
                "parse_mode": "Markdown", # Nota: Telegram "Markdown" clásico usa *negrita* (no doble asterisco)
                "disable_web_page_preview": True # Opcional: Ponlo en False si quieres que se vea la miniatura de tu web
            }
            
            try:
                # Enviamos y olvidamos (para no frenar la app)
                await client.post(url, json=payload, timeout=5.0)
                print(f"✅ Notificación enviada a {user.nick}")
            except Exception as e:
                print(f"❌ Error enviando a {user.nick}: {e}")