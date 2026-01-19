import streamlit as st
import base64
import json

def get_pwa_manifest():
    """
    Genera un Manifest JSON en base64 para inyectar en el HTML.
    Esto hace que Android/Chrome detecten la web como una App Instalable.
    """
    manifest = {
        "name": "Figus 26",
        "short_name": "Figus 26",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#FFFFFF",
        "theme_color": "#2e7d32", # Usamos el verde de tus pills para la barra de estado
        "description": "Tu álbum digital de intercambios.",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/188/188333.png", # Icono genérico de fútbol
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }
    # Convertimos a JSON string y luego a base64 data-uri
    json_str = json.dumps(manifest)
    b64_str = base64.b64encode(json_str.encode()).decode()
    return f"data:application/manifest+json;base64,{b64_str}"

def load_css():
    # Obtenemos el link del manifest
    manifest_href = get_pwa_manifest()

    st.markdown(f"""
    <link rel="manifest" href="{manifest_href}">
    <meta name="theme-color" content="#2e7d32">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

    <style>
    /* Ocultar enlaces de títulos */
    .stHeading a {{ display: none !important; }}
    [data-testid="stHeaderActionElements"] {{ display: none !important; }}
    
    /* Sidebar Ajustado */
    section[data-testid="stSidebar"] {{ min-width: 350px !important; max-width: 350px !important; }}
    section[data-testid="stSidebar"] .block-container {{ padding-top: 2rem !important; padding-bottom: 2rem !important; }}
    
    /* Espaciados */
    section[data-testid="stSidebar"] hr, 
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] .stButton, 
    section[data-testid="stSidebar"] .stProgress {{ 
        margin-bottom: 0.5rem !important; margin-top: 0.2rem !important; 
    }}
    section[data-testid="stSidebar"] h1 {{ font-size: 2rem !important; padding-bottom: 0.5rem !important; }}
    
    /* Pills Verdes */
    div[data-testid="stPills"] span[aria-selected="true"] {{ background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }}
    div[data-testid="stPills"] button[aria-selected="true"] {{ background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }}
    
    /* Botones Redondeados */
    button[kind="secondary"] {{ border-radius: 20px; }}
    
    /* Centrar Paginación */
    div[data-testid="column"] {{ text-align: center; }}

    /* Corrección altura botones */
    div.stButton > button, div.stDownloadButton > button {{ 
        min-height: 45px !important; 
        height: 45px !important;
        margin-top: 0px !important;
    }} 

    /* Botón WhatsApp/Footer Blanco */
    a[kind="secondary"] {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
        text-decoration: none !important;
    }}
    a[kind="secondary"]:hover {{
        background-color: #f0f0f0 !important;
        border-color: #999999 !important;
        color: #000000 !important;
    }}
    
    /* Footer Texto */
    .footer-text {{
        text-align: center;
        font-size: 0.8em;
        color: #888;
        margin-top: 20px;
    }}
    </style>
    """, unsafe_allow_html=True)