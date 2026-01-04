import streamlit as st

# --- CONSTANTES ---
# Recuperamos el teléfono del admin desde los secretos
try:
    ADMIN_PHONE = st.secrets["ADMIN_PHONE"]
except:
    ADMIN_PHONE = "0000000000" # Fallback por seguridad

PRECIO_PREMIUM = 5000 
MP_LINK = "https://link.mercadopago.com.ar/..." 

# --- ESTRUCTURA DEL ÁLBUM ---
ALBUM_PAGES = {
    "FW - Intro / Museos": (1, 19),
    "ARG - Argentina": (20, 39),
    "BRA - Brasil": (40, 59),
    "FRA - Francia": (60, 79),
    "USA - Estados Unidos": (80, 99),
    "MEX - México": (100, 119),
    "CAN - Canadá": (120, 139),
    "ESP - España": (140, 159),
    "Especiales Coca-Cola": (600, 608)
}

# --- TEXTOS LEGALES ---
TEXTO_LEGAL_COMPLETO = """
### TÉRMINOS Y CONDICIONES DE USO - FIGUS 26

**1. Edad Mínima y Elegibilidad**
El uso de la Aplicación está estrictamente reservado para personas **mayores de 18 años**.

**2. Naturaleza del Servicio**
Figus 26 actúa exclusivamente como una plataforma tecnológica de **conexión e información**.

**3. Seguridad en Encuentros Presenciales**
**Figus 26 NO se hace responsable** por la seguridad física, robos, hurtos o fraudes. Los encuentros son bajo su **exclusiva responsabilidad**.

**4. Privacidad**
Su "Nick", "Zona" y "Teléfono" serán visibles para otros usuarios registrados.

**5. Conducta**
Se prohíbe el acoso, spam o venta de artículos ilegales.

**6. Reputación**
Las calificaciones son referenciales y basadas en opiniones de terceros.

**7. Pagos**
Los pagos Premium no son reembolsables salvo error técnico.
"""