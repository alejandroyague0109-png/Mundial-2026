from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, Response
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
import os
import sentry_sdk
import qrcode
import io

# Imports internos
from app.database import engine, Base
from app.routers import auth, album, user, market, triangulation, safe_spots, heatmap
from app import models 
from app.data_album import ALBUM_STRUCTURE 

# Cargar variables de entorno
load_dotenv()

# Definís la versión mínima requerida
APP_MIN_VERSION = 1

# --- CONFIGURACIÓN DE INICIO (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Verificando/Creando tablas en la Base de Datos...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tablas listas.")
    except Exception as e:
        print(f"⚠️ Error DB: {e}")
    yield

# --- INICIO DE SENTRY ---
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=1.0,
        _experiments={
            "profiles_sample_rate": 1.0,
        },
    )

# ==========================================================
# 🚀 INSTANCIAMOS FASTAPI (Esto debe ir ANTES de cualquier @app)
# ==========================================================
app = FastAPI(title="Figus 26", version="2.0.0", lifespan=lifespan)

# --- 1. EL ENLACE INTELIGENTE (SMART LINK) ---
@app.get("/app")
async def smart_download_link(request: Request):
    """
    Redirige a la Play Store si es Android, o a la Web si es iOS/PC.
    """
    user_agent = request.headers.get("user-agent", "").lower()
    
    if "android" in user_agent:
        return RedirectResponse(
            url="https://canjealtoque26.com/?ref=poster", 
            status_code=303
        )
    else:
        return RedirectResponse(
            url="https://canjealtoque26.com/?ref=poster", 
            status_code=303
        )

# --- 2. GENERADOR DE QR PARA PÓSTERS ---
@app.get("/qr-poster")
async def generate_poster_qr():
    """
    Genera una imagen PNG del QR apuntando al Smart Link.
    Ideal para descargar e imprimir en los Puntos Seguros.
    """
    # El link maestro al que apuntará el QR
    target_url = "https://canjealtoque26.com/app"
    
    # Configuramos el QR con alta corrección de errores (Ideal para papel impreso)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, 
        box_size=15, # Tamaño grande para que no pierda calidad al imprimir
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)

    # Colores: Slate-900 (Casi negro) sobre fondo blanco
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    
    # Guardamos la imagen en un buffer de memoria
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    byte_im = buf.getvalue()

    # Devolvemos la imagen pura al navegador
    return Response(content=byte_im, media_type="image/png")

# --- 3. DESCARGA DIRECTA DEL APK ---
@app.get("/download-apk")
async def download_apk():
    """
    Fuerza la descarga del archivo .apk con los headers correctos 
    para que los navegadores no lo conviertan en .zip
    """
    apk_path = BASE_DIR / "static" / "CanjeAlToque26.apk"
    
    # Verificamos que el archivo exista para que no explote si te olvidás de subirlo
    if not apk_path.exists():
        return HTMLResponse(content="<h1>Error: Archivo APK no encontrado en el servidor.</h1>", status_code=404)
        
    return FileResponse(
        path=apk_path,
        media_type="application/vnd.android.package-archive", # <--- LA MAGIA ESTÁ ACÁ
        filename="CanjeAlToque26.apk", # Fuerza el nombre al guardar
        headers={"Content-Disposition": "attachment; filename=CanjeAlToque26.apk"}
    )

# --- RESTO DE LAS RUTAS GENERALES ---
@app.get("/delete-data-info", response_class=HTMLResponse)
async def delete_data_info_page():
    html_content = """
    <html>
        <head>
            <title>Eliminación de Datos - Canje AlToque 26</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-900 text-white font-sans p-8">
            <div class="max-w-2xl mx-auto bg-slate-800 p-6 rounded-2xl border border-slate-700 shadow-xl">
                <h1 class="text-2xl font-bold text-yellow-500 mb-4">Solicitud de Eliminación de Datos</h1>
                <p class="mb-4 text-gray-300">En <strong>Canje AlToque 26</strong>, respetamos tu privacidad. Tienes dos formas de eliminar tu cuenta y todos o algunos de tus datos asociados:</p>
                
                <div class="space-y-6">
                    <div class="bg-slate-700 p-4 rounded-lg">
                        <h2 class="font-bold text-lg mb-2">1. Desde la App (Recomendado)</h2>
                        <p class="text-sm text-gray-400">Ingresa a tu perfil, ve a la sección "Zona de Peligro" y presiona el botón <strong>"Eliminar mi cuenta"</strong>. Esto borrará instantáneamente tu inventario, chats y perfil de forma permanente.</p>
                    </div>

                    <div class="bg-slate-700 p-4 rounded-lg">
                        <h2 class="font-bold text-lg mb-2">2. Solicitud vía Web/Email</h2>
                        <p class="text-sm text-gray-400">Si no puedes acceder a la app, envía un correo a <span class="text-yellow-400">canjealtoque@gmail.com</span> con tu número de teléfono y Nick, o contáctanos por WhatsApp indicando tu deseo de darte de baja o con los datos que desees eliminar.</p>
                    </div>
                </div>

                <p class="mt-8 text-xs text-gray-500 text-center italic">Nota: Al eliminar tu cuenta, se pierden todos los beneficios Premium y no podrán ser recuperados.</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- CONEXIÓN DE ROUTERS ---
app.include_router(auth.router)
app.include_router(album.router)
app.include_router(user.router)
app.include_router(market.router)
app.include_router(triangulation.router)
app.include_router(safe_spots.router)
app.include_router(heatmap.router)

# --- CONFIGURACIÓN DE RUTAS FÍSICAS ---
BASE_DIR = Path(__file__).resolve().parent

# 1. Archivos Estáticos
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 2. Plantillas Jinja2 y Helpers
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Inyectamos el traductor globalmente al HTML
from app.translations import t
templates.env.globals["t"] = t

# --- HELPER: Formatear nombre de figurita (Ej: 19 -> ARG 1) ---
def format_sticker(sticker_num):
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            local_num = sticker_num - data["start"] + 1
            return f"{code} {local_num}"
    return f"#{sticker_num}"

# Registramos la función para usarla en TODOS los HTML
templates.env.globals['format_sticker'] = format_sticker

# --- RUTAS FINALES ---
@app.get("/.well-known/assetlinks.json")
async def asset_links():
    file_path = BASE_DIR / "static" / ".well-known" / "assetlinks.json"
    return FileResponse(file_path, media_type="application/json")

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected"}

@app.get("/")
async def root():
    return RedirectResponse(url="/login")

@app.get("/api/version", include_in_schema=False)
async def check_version():
    return {"min_version": APP_MIN_VERSION}