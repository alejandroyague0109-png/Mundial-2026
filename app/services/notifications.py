import urllib.parse
import httpx
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Inventory
# Asegúrate de importar tu configuración real.
# Si usas environment variables directo, ajusta esto:
from app.config import TELEGRAM_BOT_TOKEN 

async def notify_wishlist_match(sticker_num: int, sticker_name: str, owner: User, db: AsyncSession):
    """
    Busca usuarios Premium que tengan esta figurita en su Wishlist,
    tengan configurado Telegram y vivan en la MISMA ZONA que el dueño.
    Les envía una alerta.
    """
    
    # 1. BUSCAR INTERESADOS (Optimizado en Base de Datos)
    # Filtramos directamente por Wishlist + Premium + Telegram + Misma Zona/Provincia
    stmt = (
        select(User)
        .join(Inventory, User.id == Inventory.user_id)
        .where(
            Inventory.sticker_num == sticker_num,
            Inventory.status == 'wishlist',
            User.is_premium == True,
            User.telegram_chat_id.isnot(None),
            User.id != owner.id,  # No avisarse a uno mismo
            
            # --- FILTROS GEOGRÁFICOS ---
            User.province == owner.province,
            User.zone == owner.zone
        )
    )
    
    result = await db.execute(stmt)
    interested_users = result.scalars().all()

    # Si nadie la busca en esa zona, terminamos aquí.
    if not interested_users:
        return

    # 2. ENVIAR NOTIFICACIONES
    async with httpx.AsyncClient() as client:
        for user in interested_users:
            
            # A. Generar Deep Link (Codificamos los textos para evitar errores de URL)
            safe_sticker = urllib.parse.quote(sticker_name)
            safe_nick = urllib.parse.quote(owner.nick)
            safe_zone = urllib.parse.quote(owner.zone) 
            
            deep_link = f"https://canjealtoque26.com/market?sticker={safe_sticker}&nick={safe_nick}&zone={safe_zone}"

            # B. Construcción del Mensaje
            msg = (
                f"🚨 *¡APARECIÓ UNA DIFÍCIL EN TU ZONA!*\n\n"
                f"👤 *{owner.nick}* ({owner.zone}) acaba de publicar:\n"
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
                # Enviamos y olvidamos (timeout corto para no frenar la app)
                await client.post(url, json=payload, timeout=5.0)
                print(f"✅ Notificación Telegram enviada a {user.nick}")
            except Exception as e:
                print(f"❌ Error enviando Telegram a {user.nick}: {e}")