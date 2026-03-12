from fastapi import APIRouter, Depends, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pathlib import Path
import phonenumbers # IMPORTANTE: La nueva librería

# Imports internos
from app.database import get_db
from app.models import User
from app import locations # Importamos todo el módulo
from app.utils import (
    hash_password, 
    verify_password, 
    encrypt_phone 
)

# Configuración de rutas
router = APIRouter(tags=["Authentication"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- 1. MOSTRAR EL FORMULARIO (GET) ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Muestra la pantalla de Login/Registro.
    """
    if request.cookies.get("user_id"):
        return RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)

    # Ahora pasamos TODAS las locaciones y los PAÍSES disponibles al HTML
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "locations": locations.LOCATIONS_BY_COUNTRY,
        "countries": locations.AVAILABLE_COUNTRIES
    })

# --- 2. PROCESAR EL LOGIN (POST) ---
@router.post("/login")
async def login(
    request: Request,
    country_code: str = Form("AR"),
    phone: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Valida credenciales y crea la sesión.
    (El login no pide país, así que probamos parselo como AR por defecto 
    si no tiene el '+', o lo dejamos pasar si ya lo tiene).
    """
    error_msg = "Teléfono o contraseña incorrectos"
    
    try:
        # Intenta formatear el número para buscarlo. 
        # Si el usuario no puso el '+', asumimos que es de Argentina por ser el mercado original.
        # Si ya es un usuario internacional, debería poner el '+' y su código.
        if not phone.startswith('+'):
            phone_obj = phonenumbers.parse(phone, country_code)
        else:
            phone_obj = phonenumbers.parse(phone)
            
        clean_phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.phonenumberutil.NumberParseException:
        # Si falló el formateo, usamos lo que escribió (por compatibilidad con cuentas muy viejas)
        clean_phone = phone.replace(" ", "").replace("-", "")
    
    phone_processed = encrypt_phone(clean_phone) 
    
    result = await db.execute(select(User).where(User.phone_hash == phone_processed))
    user = result.scalars().first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": error_msg,
            "locations": locations.LOCATIONS_BY_COUNTRY,
            "countries": locations.AVAILABLE_COUNTRIES
        })

    response = RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user_id", value=str(user.id), httponly=True, max_age=2592000)
    
    return response

# --- 3. PROCESAR EL REGISTRO (POST) ---
@router.post("/register")
async def register(
    request: Request,
    nick: str = Form(...),
    country_code: str = Form(...), # NUEVO: Recibimos el país desde el select
    phone: str = Form(...),
    province: str = Form(...),
    zone: str = Form(...),
    password: str = Form(...),
    secret_question: str = Form(...),
    secret_answer: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo usuario validando su teléfono según su país.
    """
    # 1. Validación Estricta de Teléfono (La Magia de phonenumbers)
    try:
        # Le decimos a Google: "Analizá este número asumiendo que es de {country_code}"
        parsed_phone = phonenumbers.parse(phone, country_code)
        
        if not phonenumbers.is_valid_number(parsed_phone):
            raise ValueError("El número no es válido para ese país.")
            
        # Lo guardamos en formato internacional (+5492604..., +569...)
        clean_phone = phonenumbers.format_number(parsed_phone, phonenumbers.PhoneNumberFormat.E164)
        
    except (phonenumbers.phonenumberutil.NumberParseException, ValueError) as e:
        # Mensaje de ayuda dinámico
        if country_code == "AR":
            ayuda = "Asegurate de incluir el código de área completo. (Ej: 2604123456)"
        elif country_code == "UY":
            ayuda = "En Uruguay suele empezar con 09. (Ej: 099123456)"
        elif country_code == "CL":
            ayuda = "En Chile suele empezar con 9. (Ej: 912345678)"
        else:
            ayuda = "Revisá que la cantidad de dígitos sea la correcta."

        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": f"El número no es válido para ese país. {ayuda}",
            "locations": locations.LOCATIONS_BY_COUNTRY,
            "countries": locations.AVAILABLE_COUNTRIES
        })
    
    phone_processed = encrypt_phone(clean_phone)
    
    # 2. Verificar duplicados (Nick o Teléfono)
    stmt = select(User).where(or_(User.phone_hash == phone_processed, User.nick == nick))
    result = await db.execute(stmt)
    existing_user = result.scalars().first()

    if existing_user:
        msg = "Ese número de celular o ese Nick ya están registrados."
        if existing_user.nick == nick:
            msg = "El Nick elegido ya está en uso. Por favor elegí otro."
            
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": msg,
            "locations": locations.LOCATIONS_BY_COUNTRY,
            "countries": locations.AVAILABLE_COUNTRIES
        })

    # 3. Hashear secretos
    hashed_pwd = hash_password(password)
    hashed_answer = hash_password(secret_answer)

    # 4. Crear el Objeto Usuario (AHORA INCLUYE EL PAÍS)
    new_user = User(
        nick=nick,
        phone_hash=phone_processed,
        country_code=country_code, # <-- CRÍTICO PARA EL AISLAMIENTO RLS
        province=province,
        zone=zone,
        password=hashed_pwd,
        secret_question=secret_question,
        secret_answer=hashed_answer,
        is_premium=False,
        reputation=0
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # 5. Login Automático
        response = RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="user_id", value=str(new_user.id), httponly=True, max_age=2592000)
        return response

    except Exception as e:
        await db.rollback()
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": "Error interno al crear cuenta. Intenta nuevamente.",
            "locations": locations.LOCATIONS_BY_COUNTRY,
            "countries": locations.AVAILABLE_COUNTRIES
        })

# --- 4. LOGOUT ---
@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user_id")
    return response

# --- 5. RECUPERACIÓN DE CONTRASEÑA ---
@router.post("/auth/recover/step1")
async def recover_step1(request: Request, country_code: str = Form("AR"), phone: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        # 2. Reemplazamos limpiar_telefono por la validación de Google (phonenumbers)
        if not phone.startswith('+'):
            phone_obj = phonenumbers.parse(phone, country_code)
        else:
            phone_obj = phonenumbers.parse(phone)
            
        clean_phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.phonenumberutil.NumberParseException:
        # Fallback por si escriben algo muy raro
        clean_phone = phone.replace(" ", "").replace("-", "")
        
    # CAMBIO: Buscamos usando el método reversible
    phone_processed = encrypt_phone(clean_phone)
    
    result = await db.execute(select(User).where(User.phone_hash == phone_processed))
    user = result.scalars().first()

    # Caso: Usuario no encontrado
    if not user:
        return HTMLResponse("""
            <div class='bg-red-500/20 border border-red-500 p-3 rounded text-center mb-3 animate-pulse'>
                <p class='text-sm text-red-200'>❌ No encontramos ese número.</p>
            </div>
            <form hx-post="/auth/recover/step1" hx-target="#recovery-container" hx-swap="innerHTML" class="space-y-4">
                <input name="phone" type="tel" required placeholder="Celular registrado (con código de país ej: +54)" class="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg focus:border-yellow-500 text-sm text-white">
                <button type="submit" class="w-full py-2 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded transition">Intentar de nuevo</button>
            </form>
        """)

    # Caso: Usuario encontrado -> Devolver form del paso 2
    return HTMLResponse(f"""
        <div class='animate-fade-in'>
            <div class='bg-blue-900/30 border border-blue-500/50 p-3 rounded mb-4'>
                <p class='text-xs text-blue-300 font-bold uppercase'>Tu Pregunta Secreta:</p>
                <p class='text-lg font-bold text-white'>¿{user.secret_question}? </p>
            </div>
            
            <form hx-post="/auth/recover/step2" hx-target="#recovery-container" class="space-y-4">
                <input type="hidden" name="phone" value="{clean_phone}">
                
                <div>
                    <input name="secret_answer" type="password" required placeholder="Tu Respuesta..." 
                        class="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded focus:border-yellow-500 text-white text-sm">
                </div>
                
                <div>
                    <input name="new_password" type="password" required placeholder="Nueva contraseña..." 
                        class="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded focus:border-yellow-500 text-white text-sm">
                </div>

                <button type="submit" class="w-full py-2 bg-yellow-600 hover:bg-yellow-500 text-white font-bold rounded shadow-lg transition">
                    Cambiar Contraseña
                </button>
            </form>
        </div>
    """)


@router.post("/auth/recover/step2")
async def recover_step2(
    phone: str = Form(...),
    secret_answer: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Paso 2: Verifica respuesta -> Cambia password.
    """
    phone_processed = encrypt_phone(phone) # El form oculto ya nos manda el E164 limpio
    
    result = await db.execute(select(User).where(User.phone_hash == phone_processed))
    user = result.scalars().first()

    if not user or not verify_password(secret_answer, user.secret_answer):
        return HTMLResponse("""
            <div class='bg-red-500/20 border border-red-500 p-3 rounded text-center'>
                <p class='text-sm text-red-200'>❌ Respuesta incorrecta.</p>
                <button onclick="location.reload()" class='mt-2 text-xs text-white underline'>Volver a empezar</button>
            </div>
        """)

    user.password = hash_password(new_password)
    await db.commit()

    return HTMLResponse("""
        <div class='bg-green-500/20 border border-green-500 p-4 rounded text-center animate-fade-in'>
            <p class='text-2xl'>✅</p>
            <p class='text-white font-bold mb-2'>¡Contraseña Actualizada!</p>
            <p class='text-xs text-gray-300 mb-4'>Ya podés ingresar con tu nueva clave.</p>
            
            <button onclick="location.reload()" class='w-full py-2 bg-green-600 hover:bg-green-500 text-white font-bold rounded shadow'>
                Ir al Login
            </button>
        </div>
    """)

# --- RUTA TEMPORAL PARA ARREGLAR TELÉFONOS VIEJOS ---
@router.get("/api/migrate-phones-fix")
async def migrate_phones_fix(db: AsyncSession = Depends(get_db)):
    """
    Busca usuarios con teléfonos viejos o afectados por el SQL manual 
    (ej: 542604123456) y los formatea exactamente igual que los registros nuevos.
    """
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    migrados = 0
    ya_correctos = 0
    errores = 0
    
    for u in users:
        raw_phone = u.phone_hash
        if not raw_phone: 
            continue
            
        needs_migration = False
        number_to_parse = raw_phone
        country_hint = "AR"
        
        # 1. Detectar el caso SQL (Empieza con 54 y tiene 12 dígitos)
        if raw_phone.isdigit() and len(raw_phone) == 12 and raw_phone.startswith("54"):
            # Le sacamos el '54' para que queden los 10 dígitos puros (ej: 2604123456)
            number_to_parse = raw_phone[2:]
            needs_migration = True
            
        # 2. Detectar caso original intocable (10 dígitos puros)
        elif raw_phone.isdigit() and len(raw_phone) == 10:
            needs_migration = True
            
        # 3. Detectar caso SQL original con símbolo '+' (+549...)
        elif raw_phone.startswith('+'):
            needs_migration = True
            country_hint = None
            
        if needs_migration:
            try:
                # La librería analiza los 10 dígitos sabiendo que son de Argentina
                if country_hint:
                    phone_obj = phonenumbers.parse(number_to_parse, country_hint)
                else:
                    phone_obj = phonenumbers.parse(number_to_parse)
                    
                # Lo convierte al estándar perfecto (+5492604...)
                clean_phone = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
                
                # Lo pasa por TU función (que lo va a dejar exactamente igual que a los usuarios nuevos)
                nuevo_hash = encrypt_phone(clean_phone)
                
                # Solo guardamos si realmente hubo un cambio
                if u.phone_hash != nuevo_hash:
                    u.phone_hash = nuevo_hash
                    migrados += 1
                else:
                    ya_correctos += 1
                    
            except Exception as e:
                print(f"Error migrando a {u.nick} ({raw_phone}): {e}")
                errores += 1
        else:
            # Si no entró a las reglas, es porque ya es un número nuevo bien formateado y encriptado.
            ya_correctos += 1

    # Guardamos todos los cambios juntos
    await db.commit()
    
    return {
        "status": "success", 
        "mensaje": "Base de datos sincronizada con el nuevo formato.",
        "arreglados": migrados,
        "ya_estaban_bien_o_son_nuevos": ya_correctos,
        "errores": errores
    }