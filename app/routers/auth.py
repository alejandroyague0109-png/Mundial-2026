from fastapi import APIRouter, Depends, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pathlib import Path

# Imports internos
from app.database import get_db
from app.models import User
from app import locations # Importamos el diccionario de provincias/zonas
from app.utils import (
    hash_password, 
    verify_password, 
    limpiar_telefono, 
    # hash_phone_searchable, # YA NO SE USA PARA GUARDAR
    encrypt_phone # <--- NUEVO: Encriptación reversible
)

# Configuración de rutas
router = APIRouter(tags=["Authentication"])

# Configuración de templates
# Apunta a la carpeta 'app/templates'
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- 1. MOSTRAR EL FORMULARIO (GET) ---
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Muestra la pantalla de Login/Registro.
    Si el usuario ya tiene cookie, lo mandamos al álbum.
    """
    if request.cookies.get("user_id"):
        return RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)

    # IMPORTANTE: Pasamos 'locations' para que Alpine.js pueda armar los selectores
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "locations": locations.ARGENTINA 
    })

# --- 2. PROCESAR EL LOGIN (POST) ---
@router.post("/login")
async def login(
    request: Request,
    phone: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Valida credenciales y crea la sesión.
    """
    # 1. Limpiar datos de entrada
    clean_phone = limpiar_telefono(phone)
    
    # CAMBIO: Usamos encrypt_phone para buscar al usuario
    # (porque así está guardado en la DB ahora)
    phone_processed = encrypt_phone(clean_phone) 
    
    # 2. Buscar Usuario
    result = await db.execute(select(User).where(User.phone_hash == phone_processed))
    user = result.scalars().first()

    error_msg = "Teléfono o contraseña incorrectos"

    # 3. Validar (Usuario existe Y contraseña coincide con Bcrypt)
    if not user or not verify_password(password, user.password):
        # En caso de error, DEBEMOS pasar 'locations' de nuevo, 
        # sino los selectores se rompen al recargar la página.
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": error_msg,
            "locations": locations.ARGENTINA
        })

    # 4. ÉXITO: Crear Cookie y Redirigir
    response = RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)
    # Cookie segura, dura 30 días
    response.set_cookie(key="user_id", value=str(user.id), httponly=True, max_age=2592000)
    
    return response

# --- 3. PROCESAR EL REGISTRO (POST) ---
@router.post("/register")
async def register(
    request: Request,
    nick: str = Form(...),
    phone: str = Form(...),
    province: str = Form(...),
    zone: str = Form(...),
    password: str = Form(...),
    secret_question: str = Form(...),
    secret_answer: str = Form(...),
    # tyc: bool = Form(...) # El checkbox 'required' del HTML ya valida que esto venga en True
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo usuario con todos los datos requeridos.
    """
    # 1. Limpieza
    clean_phone = limpiar_telefono(phone)
    
    # CAMBIO CRÍTICO: Usamos encrypt_phone (Reversible) al registrar
    phone_processed = encrypt_phone(clean_phone)
    
    # 2. Verificar duplicados (Nick o Teléfono)
    # Buscamos si ya existe alguien con ese teléfono O ese nick
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
            "locations": locations.ARGENTINA
        })

    # 3. Hashear secretos (Password y Respuesta de seguridad)
    hashed_pwd = hash_password(password)
    hashed_answer = hash_password(secret_answer)

    # 4. Crear el Objeto Usuario
    new_user = User(
        nick=nick,
        phone_hash=phone_processed, # Guardamos el valor reversible
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
        
        # 5. Login Automático (Redirigir directo al álbum)
        response = RedirectResponse(url="/album", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="user_id", value=str(new_user.id), httponly=True, max_age=2592000)
        return response

    except Exception as e:
        await db.rollback()
        return templates.TemplateResponse("auth/login.html", {
            "request": request, 
            "error": "Error interno al crear cuenta. Intenta nuevamente.",
            "locations": locations.ARGENTINA
        })

# --- 4. LOGOUT ---
@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user_id")
    return response

# --- 5. RECUPERACIÓN DE CONTRASEÑA ---

@router.post("/auth/recover/step1")
async def recover_step1(request: Request, phone: str = Form(...), db: AsyncSession = Depends(get_db)):
    try:
        clean_phone = limpiar_telefono(phone)
        
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
                    <input name="phone" type="tel" required placeholder="Celular registrado" class="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg focus:border-yellow-500 text-sm text-white">
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
                    <input type="hidden" name="phone" value="{phone}">
                    
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
        
    except Exception as e:
        print(f"❌ ERROR EN RECOVERY: {e}") # Mira esto en la consola de VS Code
        return HTMLResponse(f"<div class='text-red-500'>Error interno: {e}</div>")


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
    clean_phone = limpiar_telefono(phone)
    
    # CAMBIO: Usamos encrypt_phone
    phone_processed = encrypt_phone(clean_phone)
    
    result = await db.execute(select(User).where(User.phone_hash == phone_processed))
    user = result.scalars().first()

    # Validación de seguridad
    if not user or not verify_password(secret_answer, user.secret_answer):
        return HTMLResponse("""
            <div class='bg-red-500/20 border border-red-500 p-3 rounded text-center'>
                <p class='text-sm text-red-200'>❌ Respuesta incorrecta.</p>
                <button onclick="location.reload()" class='mt-2 text-xs text-white underline'>Volver a empezar</button>
            </div>
        """)

    # ÉXITO: Cambiar contraseña
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