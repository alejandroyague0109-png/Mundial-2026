import os
import mercadopago
from fastapi import APIRouter, Depends, Request, Form, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, delete, text
from dotenv import load_dotenv

from app.database import get_db
from app.models import User
from app.locations import ARGENTINA
# Importamos desde el nuevo archivo de dependencias
from app.dependencies import get_current_user

# Cargar variables de entorno (MP_ACCESS_TOKEN)
load_dotenv()

router = APIRouter(tags=["User"])

# --- 1. OBTENER LOCALIDADES (Cascading Select) ---
@router.get("/locations/zones")
async def get_zones_for_province(province: str):
    zones = ARGENTINA.get(province, [])
    options = f'<option value="" disabled selected>Seleccioná tu zona</option>'
    options += "".join([f'<option value="{z}">{z}</option>' for z in zones])
    return Response(content=options, media_type="text/html")

# --- 2. ACTUALIZAR PERFIL (SOLO UBICACIÓN) ---
@router.post("/update_profile")
async def update_profile(
    request: Request,
    province: str = Form(...),
    zone: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)

    stmt = update(User).where(User.id == int(user_id)).values(province=province, zone=zone)
    await db.execute(stmt)
    await db.commit()

    html_response = """
    <div id="toast-loc" class="fixed bottom-5 right-5 bg-green-600 text-white px-6 py-3 rounded-lg shadow-2xl flex items-center gap-3 animate-slide-up z-50 border border-green-400">
        <span class="text-xl">📍</span>
        <div><h4 class="font-bold text-sm">Ubicación Guardada</h4></div>
    </div>
    <script>
        const modal = document.getElementById('profileModal');
        if (modal) modal.close();
        setTimeout(() => { window.location.reload(); }, 1000);
    </script>
    <style>@keyframes slideUpToast { from { transform: translateY(100%); opacity: 0; } to { transform: translateY(0); opacity: 1; } } .animate-slide-up { animation: slideUpToast 0.3s ease-out forwards; }</style>
    """
    return Response(content=html_response, media_type="text/html")

# --- 3. ACTUALIZAR TELEGRAM (SOLO NOTIFICACIONES) ---
@router.post("/update_telegram")
async def update_telegram(
    request: Request,
    telegram_id: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)
    
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()

    if not user: return Response(status_code=404)
    if not user.is_premium:
        return Response(content="<div class='text-red-400 text-xs'>Función Premium 🔒</div>", media_type="text/html")

    tg_val = telegram_id.strip() if telegram_id else None
    await db.execute(update(User).where(User.id == int(user_id)).values(telegram_chat_id=tg_val))
    await db.commit()

    html_response = """
    <div id="toast-tg" class="fixed bottom-5 right-5 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-2xl flex items-center gap-3 animate-slide-up z-50 border border-blue-400">
        <span class="text-xl">🤖</span>
        <div><h4 class="font-bold text-sm">Alertas Configuradas</h4></div>
    </div>
    <script>
        const modal = document.getElementById('telegramModal');
        if (modal) modal.close();
        setTimeout(() => { document.getElementById('toast-tg')?.remove(); }, 2500);
    </script>
    <style>.animate-slide-up { animation: slideUpToast 0.3s ease-out forwards; }</style>
    """
    return Response(content=html_response, media_type="text/html")


# ==============================================================================
#   INTEGRACIÓN MERCADO PAGO: CHECKOUT PRO (AUTOMÁTICO) + WEBHOOKS
# ==============================================================================

# --- 4. CREAR PREFERENCIA (Al hacer clic en "Activar Premium") ---
@router.get("/create_preference")
async def create_preference(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    print(f"--- 🚀 INTENTO DE PAGO: Usuario {current_user.id} ---")

    token = os.getenv("MP_ACCESS_TOKEN")
    if not token:
        return {"error": "Falta Token MP"}

    sdk = mercadopago.SDK(token)
    
    # --- CORRECCIÓN FINAL: URL REAL ---
    # Usamos tu dominio real directamente para asegurar que MP lo acepte.
    # (Si cambias de dominio en el futuro, recuerda actualizar esto o usar una variable de entorno DOMAIN)
    base_url = "https://mundial-2026-production.up.railway.app"

    preference_data = {
        "items": [
            {
                "id": "premium_upgrade",
                "title": "Suscripción Premium - Canje AlToque 26",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": 5000.0
            }
        ],
        "payer": {
            # Email genérico obligatorio
            "email": "usuario_app@canjealtoque.com" 
        },
        "back_urls": {
            # Definimos explícitamente a dónde volver
            "success": f"{base_url}/payment_callback",
            "failure": f"{base_url}/payment_callback",
            "pending": f"{base_url}/payment_callback"
        },
        "auto_return": "approved", # Esto obliga a que back_urls.success exista y sea válido
        
        "notification_url": f"{base_url}/webhook", 
        "external_reference": str(current_user.id),
        
        "payment_methods": {
            "excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}]
        }
    }

    try:
        result = sdk.preference().create(preference_data)
        response_body = result.get("response", {})
        
        if result.get("status") not in [200, 201]:
            print(f"❌ ERROR MP DETALLE: {response_body}")
            return {
                "error": "Rechazado por Mercado Pago",
                "detalle": response_body
            }

        # Elegir link (Sandbox o Prod)
        url = response_body.get("init_point")
        if "TEST" in token:
            url = response_body.get("sandbox_init_point")
            
        print(f"✅ LINK OK: {url}")
        return RedirectResponse(url=url, status_code=303)

    except Exception as e:
        print(f"❌ CRASH: {e}")
        return {"error": str(e)}

# --- 5. WEBHOOK (Notificación Invisible) ---
@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        params = request.query_params
        topic = params.get("topic") or params.get("type")
        payment_id = params.get("id") or params.get("data.id")

        if topic == "payment" and payment_id:
            token = os.getenv("MP_ACCESS_TOKEN")
            sdk = mercadopago.SDK(token)
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info.get("response", {})

            status = payment.get("status")
            external_ref = payment.get("external_reference")

            if status == "approved" and external_ref:
                user_id = int(external_ref)
                await db.execute(update(User).where(User.id == user_id).values(is_premium=True))
                await db.commit()
                print(f"✅ Webhook: Usuario {user_id} actualizado a Premium.")
        
        return Response(status_code=200)
    except Exception as e:
        print(f"❌ Error Webhook: {e}")
        return Response(status_code=500)


# --- 6. CALLBACK DE RETORNO (El usuario vuelve de MP) ---
@router.get("/payment_callback")
async def payment_callback(
    request: Request,
    collection_status: str = "",
    external_reference: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Maneja el retorno del usuario desde Mercado Pago"""
    
    # Solo si el estado es aprobado y tenemos la referencia del usuario
    if collection_status == "approved" and external_reference:
        try:
            target_user_id = int(external_reference)
            
            # ACTIVAR PREMIUM
            await db.execute(
                update(User)
                .where(User.id == target_user_id)
                .values(is_premium=True)
            )
            await db.commit()
            
            # Redirigir al inicio con flag de éxito para mostrar confetti
            return RedirectResponse(url="/?payment_success=true", status_code=303)
        except Exception as e:
            print(f"Error procesando callback: {e}")
            return RedirectResponse(url="/?payment_error=true", status_code=303)
    
    # Si canceló o falló
    return RedirectResponse(url="/?payment_error=true", status_code=303)


# --- 7. VALIDACIÓN MANUAL (Respaldo) ---
@router.post("/validate_payment")
async def validate_payment(
    request: Request,
    payment_id: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)

    pid = payment_id.strip()
    if not pid:
        return Response(content="<div class='text-xs text-red-400 mt-2'>❌ Ingresá un ID.</div>", media_type="text/html")

    token = os.getenv("MP_ACCESS_TOKEN")
    if not token:
        return Response(content="<div class='text-xs text-red-400 mt-2'>❌ Error config servidor.</div>", media_type="text/html")

    sdk = mercadopago.SDK(token)

    try:
        payment_info = sdk.payment().get(pid)
        
        if payment_info["status"] == 404:
             return Response(content="<div class='text-xs text-red-400 mt-2'>❌ Pago no encontrado.</div>", media_type="text/html")

        payment_data = payment_info.get("response", {})
        status = payment_data.get("status")
        amount = payment_data.get("transaction_amount", 0)

        if status == "approved" and amount >= 5000:
            await db.execute(update(User).where(User.id == int(user_id)).values(is_premium=True))
            await db.commit()

            html_response = """
            <div id="toast-premium" class="fixed inset-0 flex items-center justify-center bg-black/80 z-[60] animate-fade-in">
                <div class="bg-slate-900 p-8 rounded-2xl border-2 border-yellow-500 text-center shadow-[0_0_50px_rgba(234,179,8,0.5)] transform scale-110">
                    <div class="text-6xl mb-4">🎉</div>
                    <h2 class="text-3xl font-black text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 to-yellow-600 mb-2">¡PAGO APROBADO!</h2>
                    <p class="text-gray-300">Bienvenido a Primera División.</p>
                    <p class="text-sm text-gray-500 mt-4">Actualizando...</p>
                </div>
            </div>
            <script>
                const modal = document.getElementById('premiumModal');
                if (modal) modal.close();
                setTimeout(() => { window.location.reload(); }, 2500);
            </script>
            <style>.animate-fade-in { animation: fadeIn 0.5s ease-out; }</style>
            """
            return Response(content=html_response, media_type="text/html")
        
        elif status == "pending":
            return Response(content="<div class='text-xs text-yellow-400 mt-2'>⏳ Pago pendiente.</div>", media_type="text/html")
        else:
            return Response(content=f"<div class='text-xs text-red-400 mt-2'>❌ Estado: {status}.</div>", media_type="text/html")

    except Exception as e:
        print(f"Error MP: {e}")
        return Response(content="<div class='text-xs text-red-400 mt-2'>❌ Error de conexión.</div>", media_type="text/html")

# ==============================================================================
#   8. WEBHOOK B2B (EXCLUSIVO PARA EL BOT DE WHATSAPP B2B)
# ==============================================================================
@router.post("/webhook_b2b")
async def receive_webhook_b2b(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        params = request.query_params
        topic = params.get("topic") or params.get("type")
        payment_id = params.get("id") or params.get("data.id")

        if topic == "payment" and payment_id:
            # ⚠️ CLAVE: Usamos una variable de entorno DIFERENTE para el token del Bot
            token_b2b = os.getenv("MP_ACCESS_TOKEN_B2B")
            
            if not token_b2b:
                print("❌ Error: Falta configurar MP_ACCESS_TOKEN_B2B en Railway")
                return Response(status_code=500)

            sdk = mercadopago.SDK(token_b2b)
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info.get("response", {})

            status = payment.get("status")
            external_ref = payment.get("external_reference") # Este será el UUID del comercio

            if status == "approved" and external_ref:
                # Usamos SQL puro para actualizar Supabase sin necesidad de modelos de SQLAlchemy
                query = text("""
                    UPDATE puntos_seguros 
                    SET verificado = true, estado_limpieza = 'pagado_confirmado' 
                    WHERE id = :local_id
                """)
                await db.execute(query, {"local_id": external_ref})
                await db.commit()
                
                print(f"✅ Webhook B2B: ¡PAGO RECIBIDO! Local {external_ref} ahora está Verificado.")
        
        return Response(status_code=200)
    except Exception as e:
        print(f"❌ Error Crítico en Webhook B2B: {e}")
        return Response(status_code=500)

# --- 9. ELIMINAR CUENTA (DANGER ZONE) ---
@router.post("/delete_account")
async def delete_account(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    # Si no hay usuario, redirigimos al home
    if not user_id: 
        return RedirectResponse(url="/", status_code=303)

    try:
        # Ejecutamos el borrado
        # Nota: Al borrar el usuario, la base de datos debería borrar en cascada
        # sus inventarios y notificaciones si las Foreign Keys tienen 'ON DELETE CASCADE'.
        await db.execute(delete(User).where(User.id == int(user_id)))
        await db.commit()
    except Exception as e:
        print(f"Error borrando usuario: {e}")
        # Si falla, podrías devolver un error, pero por seguridad redirigimos igual
    
    # Preparamos la respuesta para sacar al usuario
    response = RedirectResponse(url="/?deleted=true", status_code=303)
    response.delete_cookie("user_id") # Borramos la cookie de sesión
    return response