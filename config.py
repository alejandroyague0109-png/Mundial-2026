import os
import streamlit as st

# Intenta leer de entorno, si no, de secretos
ADMIN_PHONE = os.environ.get("ADMIN_PHONE")
if not ADMIN_PHONE:
    try:
        ADMIN_PHONE = st.secrets["ADMIN_PHONE"]
    except:
        ADMIN_PHONE = "SIN_CONFIGURAR" # Evita que explote si no encuentra nada

# --- TELEGRAM (SEGURO) ---
# Leemos el token desde los secretos de Streamlit para no exponerlo en GitHub.
# Si estás en local, asegurate de tenerlo en .streamlit/secrets.toml
try:
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
except Exception:
    # Valor por defecto para evitar que la app crashee si no hay secrets configurados
    TELEGRAM_BOT_TOKEN = "TOKEN_NO_CONFIGURADO"

# --- DATOS DEL ÁLBUM (Mundial 2026) ---
# Estructura: "NOMBRE_PAIS": (ID_INICIAL, ID_FINAL)
ALBUM_PAGES = {
    "ARG - Argentina": (1, 19),
    "BRA - Brasil": (20, 38),
    "FRA - Francia": (39, 57),
    "GER - Alemania": (58, 76),
    "ESP - España": (77, 95),
    "ENG - Inglaterra": (96, 114),
    "ITA - Italia": (115, 133),
    "USA - Estados Unidos": (134, 152),
    "MEX - México": (153, 171),
    "CAN - Canadá": (172, 190),
    "FWC - Museos / Especiales": (191, 200)
}

# --- PREMIUM ---
PRECIO_PREMIUM = 5000
MP_LINK = "https://mpago.la/1DR8e6S"

# --- LEGALES ROBUSTOS ---
TEXTO_LEGAL_COMPLETO = """
**TÉRMINOS Y CONDICIONES DE USO - FIGUS 26**

**1. ACEPTACIÓN DE RIESGOS**
Al utilizar esta aplicación, usted comprende y acepta que Figus 26 actúa exclusivamente como un tablón de anuncios digital para conectar coleccionistas. **No participamos, supervisamos ni garantizamos** los intercambios físicos ni las transacciones monetarias.

**2. DESLINDE DE RESPONSABILIDAD**
Figus 26 y sus desarrolladores **no se hacen responsables** por:
* Encuentros fallidos, robos, hurtos o agresiones que pudieran ocurrir durante los canjes presenciales.
* Figuritas falsas, dañadas o que no correspondan con lo publicado.
* Estafas económicas, billetes falsos o transferencias no recibidas.
* El uso indebido de los datos de contacto por parte de otros usuarios.

**3. REGLAS DE SEGURIDAD OBLIGATORIAS**
El usuario se compromete a:
* Realizar los intercambios **únicamente en lugares públicos, concurridos y de día** (ej: plazas céntricas, centros comerciales, estaciones de servicio).
* No compartir información sensible (dirección de casa, horarios laborales) con desconocidos.
* Verificar el material antes de finalizar el canje.

**4. PRIVACIDAD**
Su número de teléfono se mantendrá encriptado y solo será revelado a otro usuario cuando este utilice explícitamente la función "Contactar" bajo el sistema de créditos o suscripción Premium.

**5. DERECHO DE ADMISIÓN**
Nos reservamos el derecho de suspender o eliminar permanentemente cuentas que:
* Reciban múltiples reportes de fraude o mal comportamiento.
* Utilicen lenguaje ofensivo, discriminatorio o de acoso.
* Intenten comercializar artículos ilegales o ajenos al coleccionismo de figuritas.

**Al hacer clic en "Acepto", usted declara ser mayor de 18 años y libera a Figus 26 de toda responsabilidad civil o penal derivada del uso de la plataforma.**
"""