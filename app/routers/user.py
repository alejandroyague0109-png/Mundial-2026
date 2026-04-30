import os
import mercadopago
import httpx  # <-- AGREGAR ESTO PARA PAYPAL
from fastapi import APIRouter, Depends, Request, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, delete, text
from dotenv import load_dotenv


from app.database import get_db
from app.models import User
from app.locations import LOCATIONS_BY_COUNTRY
# Importamos desde el nuevo archivo de dependencias
from app.dependencies import get_current_user

# Cargar variables de entorno (MP_ACCESS_TOKEN)
load_dotenv()

router = APIRouter(tags=["User"])


# --- 1. OBTENER LOCALIDADES Y ZONAS (Cascading Select) ---

@router.get("/locations/provinces")
async def get_provinces_for_country(country_code: str = "AR"):
    country_data = LOCATIONS_BY_COUNTRY.get(country_code, {})
    provinces = country_data.keys()
    
    options = '<option value="" disabled selected>Seleccioná tu provincia</option>'
    options += "".join([f'<option value="{p}">{p}</option>' for p in provinces])
    
    # Truco de HTMX: Al cambiar el país, reseteamos también el select de la zona
    options += '<script>document.getElementById("zone-select").innerHTML = \'<option value="" disabled selected>Seleccioná tu zona</option>\';</script>'
    
    return Response(content=options, media_type="text/html")

@router.get("/locations/zones")
async def get_zones_for_province(country_code: str = "AR", province: str = ""):
    # Buscamos las zonas cruzando país y provincia
    country_data = LOCATIONS_BY_COUNTRY.get(country_code, {})
    zones = country_data.get(province, [])
    
    options = f'<option value="" disabled selected>Seleccioná tu zona</option>'
    options += "".join([f'<option value="{z}">{z}</option>' for z in zones])
    return Response(content=options, media_type="text/html")

# --- 2. ACTUALIZAR PERFIL (SOLO UBICACIÓN) ---
@router.post("/update_profile")
async def update_profile(
    request: Request,
    country_code: str = Form(...), # <-- Nuevo campo recibido
    province: str = Form(...),
    zone: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    user_id = request.cookies.get("user_id")
    if not user_id: return Response(status_code=401)

    stmt = update(User).where(User.id == int(user_id)).values(country_code=country_code, province=province, zone=zone)
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
# --- 4. CREAR PREFERENCIA (MERCADO PAGO O PAYPAL) ---
@router.get("/create_preference")
async def create_preference(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) 
):
    print(f"--- 🚀 INTENTO DE PAGO: Usuario {current_user.id} - País: {current_user.country_code} ---")
    base_url = "https://mundial-2026-production.up.railway.app"
    country = current_user.country_code if current_user.country_code else "AR"

    # --- FLUJO ARGENTINA: MERCADO PAGO ---
    if country == "AR":
        token = os.getenv("MP_ACCESS_TOKEN")
        if not token: return {"error": "Falta Token MP"}

        sdk = mercadopago.SDK(token)
        preference_data = {
            "items": [{
                "id": "premium_upgrade", "title": "Suscripción Premium - Canje AlToque 26",
                "quantity": 1, "currency_id": "ARS", "unit_price": 4999.99
            }],
            "payer": {"email": "usuario_app@canjealtoque.com"},
            "purpose": "wallet_purchase",
            "back_urls": {
                "success": f"{base_url}/payment_callback",
                "failure": f"{base_url}/payment_callback",
                "pending": f"{base_url}/payment_callback"
            },
            "auto_return": "approved",
            "notification_url": f"{base_url}/webhook", 
            "external_reference": str(current_user.id),
            "payment_methods": {"excluded_payment_types": [{"id": "ticket"}, {"id": "atm"}]}
        }

        try:
            result = sdk.preference().create(preference_data)
            response_body = result.get("response", {})
            if result.get("status") not in [200, 201]:
                return {"error": "Rechazado por Mercado Pago", "detalle": response_body}

            url = response_body.get("init_point")
            if "TEST" in token: url = response_body.get("sandbox_init_point")
            return RedirectResponse(url=url, status_code=303)
        except Exception as e:
            return {"error": str(e)}

    # --- FLUJO RESTO DEL MUNDO: PAYPAL ---
    else:
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        secret = os.getenv("PAYPAL_SECRET")
        mode = os.getenv("PAYPAL_MODE", "sandbox") 

        if not client_id or not secret:
            return {"error": "Faltan credenciales de PayPal."}

        api_base = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"

        async with httpx.AsyncClient() as client:
            try:
                # 1. Autenticar con PayPal
                auth_res = await client.post(
                    f"{api_base}/v1/oauth2/token",
                    auth=(client_id, secret),
                    data={"grant_type": "client_credentials"}
                )
                access_token = auth_res.json().get("access_token")
                if not access_token: return {"error": "Error auth PayPal"}

                # 2. Crear Orden de 4 USD
                order_payload = {
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": str(current_user.id),
                        "description": "Suscripción Premium - Canje AlToque 26",
                        "amount": {"currency_code": "USD", "value": "3.99"}
                    }],
                    "application_context": {
                        "return_url": f"{base_url}/paypal_capture", # <-- LIMPIO, SIN USER ID
                        "cancel_url": f"{base_url}/?payment_error=true",
                        "brand_name": "Canje AlToque 26",
                        "landing_page": "BILLING",
                        "user_action": "PAY_NOW"
                    }
                }

                order_res = await client.post(
                    f"{api_base}/v2/checkout/orders",
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json=order_payload
                )
                order_data = order_res.json()

                # 3. Redirigir al link de pago
                for link in order_data.get("links", []):
                    if link.get("rel") == "approve":
                        return RedirectResponse(url=link["href"], status_code=303)
                return {"error": "PayPal no devolvió link", "detalle": order_data}

            except Exception as e:
                print(f"❌ Error PayPal: {e}")
                return {"error": "Error conectando con PayPal"}

# --- NUEVA RUTA: CAPTURA DE PAYPAL (El usuario vuelve de PayPal) ---
@router.get("/paypal_capture")
async def paypal_capture(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    
    # 🛡️ SEGURIDAD: Obtenemos el usuario de la cookie, es inhackeable por URL
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie:
        return RedirectResponse(url="/?payment_error=true", status_code=303)
    user_id = int(user_id_cookie)

    client_id = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_SECRET")
    
    # ... (el resto del código de la función queda exactamente igual) ...
    mode = os.getenv("PAYPAL_MODE", "sandbox")
    api_base = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"

    async with httpx.AsyncClient() as client:
        try:
            # 1. Autenticación
            auth_res = await client.post(
                f"{api_base}/v1/oauth2/token",
                auth=(client_id, secret),
                data={"grant_type": "client_credentials"}
            )
            access_token = auth_res.json().get("access_token")

            # 2. Capturar Fondos (PayPal exige hacer esto para confirmar el cobro)
            capture_res = await client.post(
                f"{api_base}/v2/checkout/orders/{token}/capture",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            )
            capture_data = capture_res.json()

            # 3. Validar y dar Premium
            if capture_data.get("status") == "COMPLETED":
                await db.execute(update(User).where(User.id == user_id).values(is_premium=True))
                await db.commit()
                print(f"✅ PayPal Success: Usuario {user_id} es Premium.")
                return RedirectResponse(url="/?payment_success=true", status_code=303)
            else:
                print(f"❌ PayPal Falla/Pendiente: {capture_data}")
                return RedirectResponse(url="/?payment_error=true", status_code=303)
                
        except Exception as e:
            print(f"Error procesando captura de PayPal: {e}")
            return RedirectResponse(url="/?payment_error=true", status_code=303)


# --- NUEVA RUTA B2B: CAPTURA DE PAYPAL (Los locales vuelven de pagar su plan) ---
@router.get("/paypal_capture_b2b")
async def paypal_capture_b2b(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_SECRET")
    mode = os.getenv("PAYPAL_MODE", "sandbox")
    api_base = "https://api-m.paypal.com" if mode == "live" else "https://api-m.sandbox.paypal.com"

    async with httpx.AsyncClient() as client:
        try:
            # 1. Autenticación con PayPal
            auth_res = await client.post(
                f"{api_base}/v1/oauth2/token",
                auth=(client_id, secret),
                data={"grant_type": "client_credentials"}
            )
            access_token = auth_res.json().get("access_token")

            if not access_token:
                print("❌ Error de Auth con PayPal B2B")
                return RedirectResponse(url="https://canjealtoque26.com?payment_error=true", status_code=303)

            # 2. Capturar Fondos (Confirma la transacción)
            capture_res = await client.post(
                f"{api_base}/v2/checkout/orders/{token}/capture",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            )
            capture_data = capture_res.json()

            # 3. Validar y dar de alta el local
            if capture_data.get("status") == "COMPLETED":
                # Extraemos el UUID del local que inyectaste desde Node.js en reference_id
                purchase_units = capture_data.get("purchase_units", [])
                if purchase_units:
                    local_uuid = purchase_units[0].get("reference_id")
                    
                    if local_uuid:
                        # Actualizamos Supabase forzando el casteo a UUID
                        query = text("""
                            UPDATE puntos_seguros 
                            SET verificado = true 
                            WHERE id = :local_id::uuid
                        """)
                        await db.execute(query, {"local_id": local_uuid})
                        await db.commit()
                        
                        print(f"✅ PayPal Success B2B: Local {local_uuid} ahora está Verificado.")
                        
                        # Redirigimos al local a la web oficial mostrando éxito
                        return RedirectResponse(url="https://canjealtoque26.com?payment_success=true", status_code=303)
            
            print(f"❌ PayPal Falla/Pendiente B2B: {capture_data}")
            return RedirectResponse(url="https://canjealtoque26.com?payment_error=true", status_code=303)
                
        except Exception as e:
            print(f"Error procesando captura de PayPal B2B: {e}")
            return RedirectResponse(url="https://canjealtoque26.com?payment_error=true", status_code=303)

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
                # Usamos SQL puro forzando el casteo a UUID
                query = text("""
                    UPDATE puntos_seguros 
                    SET verificado = true 
                    WHERE id = :local_id::uuid
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

# --- 10. POLÍTICA DE ELIMINACIÓN DE DATOS (REQUISITO GOOGLE PLAY) ---
@router.get("/delete-data-info", response_class=HTMLResponse)
async def delete_data_info():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Eliminación de Datos - CanjeAlToque2026 Álbum Mundial</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
            h1 { color: #1e40af; }
            .info-box { background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <h1>Política de Eliminación de Datos y Cuenta</h1>
        
        <div class="info-box">
            <p><strong>Aplicación: </strong>CanjeAlToque2026 Álbum Mundial</p>
            <p><strong>Desarrollador: </strong>Trading Devs</p>
        </div>

        <h2>¿Cómo eliminar tu cuenta y tus datos?</h2>
        <p>De acuerdo con las políticas de Google Play, ofrecemos a nuestros usuarios opciones claras para eliminar su cuenta y todos los datos asociados (como tu inventario de figuritas y ubicación).</p>
        
        <h3>Opción 1: Desde la aplicación</h3>
        <p>Puedes eliminar tu cuenta en cualquier momento directamente desde la app. Ve a tu Perfil, selecciona "Configuración" y presiona el botón rojo que dice "Eliminar Cuenta". Esta acción borrará inmediatamente tu usuario de nuestra base de datos.</p>

        <h3>Opción 2: Solicitud vía web/correo electrónico</h3>
        <p>Si ya desinstalaste la aplicación y deseas que borremos tus datos, puedes solicitar la eliminación enviando un correo electrónico a nuestro equipo de soporte.</p>
        <ul>
            <li><strong>Correo de contacto:</strong> <em>canjealtoque@gmail.com</em></li>
            <li><strong>Asunto:</strong> Solicitud de Eliminación de Cuenta - CanjeAlToque2026</li>
            <li><strong>Cuerpo del mensaje:</strong> Por favor, incluye el número de teléfono con el que te registraste en la aplicación para que podamos identificar y borrar tu información de nuestros servidores.</li>
        </ul>
        <p>Procesaremos tu solicitud y eliminaremos todos tus datos en un plazo máximo de 7 días hábiles.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)