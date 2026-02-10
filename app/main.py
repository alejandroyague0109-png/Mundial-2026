from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
import os # Asegurate de tener este import
import sentry_sdk # Nuevo import

# Imports internos
from app.database import engine, Base
from app.routers import auth, album, user, market, triangulation
from app import models 
from app.data_album import ALBUM_STRUCTURE # Necesario para el helper

# Cargar variables de entorno
load_dotenv()

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

# --- CONEXIÓN DE ROUTERS ---
app.include_router(auth.router)
app.include_router(album.router)
app.include_router(user.router)
app.include_router(market.router)
app.include_router(triangulation.router)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = Path(__file__).resolve().parent

# 1. Archivos Estáticos
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 2. Plantillas Jinja2 y Helpers
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

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
@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected"}

@app.get("/")
async def root():
    return RedirectResponse(url="/login")