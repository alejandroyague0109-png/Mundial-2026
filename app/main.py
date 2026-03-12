from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
import os # Asegurate de tener este import
import sentry_sdk # Nuevo import

# Imports internos
from app.database import engine, Base
from app.routers import auth, album, users, market, triangulation, safe_spots, heatmap
from app import models 
from app.data_album import ALBUM_STRUCTURE # Necesario para el helper

# Cargar variables de entorno
load_dotenv()

# Definís la versión mínima requerida al principio de tu archivo o en tus variables
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

# --- INICIO DE SENTRY (Pegar antes de app = FastAPI) ---
# Solo iniciamos Sentry si existe la variable de entorno, para no molestar en local
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        # Captura el 100% de los errores para análisis
        traces_sample_rate=1.0,
        _experiments={
            "profiles_sample_rate": 1.0,
        },
    )

# Instanciamos FastAPI
app = FastAPI(title="Figus 26", version="2.0.0", lifespan=lifespan)

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

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent

# 1. Archivos Estáticos
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 2. Plantillas Jinja2 y Helpers
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- NUEVO: Inyectamos el traductor globalmente al HTML ---
from app.translations import t
templates.env.globals["t"] = t
# ----------------------------------------------------------

# --- HELPER: Formatear nombre de figurita (Ej: 19 -> ARG 1) ---
def format_sticker(sticker_num):
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= sticker_num < data["start"] + data["count"]:
            local_num = sticker_num - data["start"] + 1
            return f"{code} {local_num}"
    return f"#{sticker_num}"

# Registramos la función para usarla en TODOS los HTML
templates.env.globals['format_sticker'] = format_sticker

# --- RUTAS GENERALES ---

@app.get("/.well-known/assetlinks.json")
async def asset_links():
    # La ruta física será: app/static/.well-known/assetlinks.json
    file_path = BASE_DIR / "static" / ".well-known" / "assetlinks.json"
    return FileResponse(file_path, media_type="application/json")

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected"}

@app.get("/")
async def root():
    return RedirectResponse(url="/login")

# Agregás la ruta para que el frontend pregunte
@app.get("/api/version", include_in_schema=False)
async def check_version():
    return {"min_version": APP_MIN_VERSION}