import streamlit as st
import base64
import json

def get_pwa_manifest():
    """Genera un Manifest JSON en base64 para PWA."""
    manifest = {
        "name": "Figus 26",
        "short_name": "Figus 26",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#FFFFFF",
        "theme_color": "#2e7d32",
        "description": "Tu álbum digital de intercambios.",
        "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/188/188333.png", "sizes": "192x192", "type": "image/png"}]
    }
    json_str = json.dumps(manifest)
    b64_str = base64.b64encode(json_str.encode()).decode()
    return f"data:application/manifest+json;base64,{b64_str}"

def load_css():
    manifest_href = get_pwa_manifest()

    st.markdown(f"""
    <link rel="manifest" href="{manifest_href}">
    <meta name="theme-color" content="#2e7d32">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

    <style>
    /* Ocultar elementos default de Streamlit */
    .stHeading a {{ display: none !important; }}
    [data-testid="stHeaderActionElements"] {{ display: none !important; }}
    footer {{ display: none !important; }}
    
    /* === BOTTOM NAVBAR FIJA (Clave para UX Móvil) === */
    .fixed-bottom-nav {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 70px; /* Altura de la barra */
        background-color: #ffffff;
        border-top: 1px solid #e0e0e0;
        z-index: 999999;
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 0 10px;
        box-shadow: 0px -2px 10px rgba(0,0,0,0.05);
    }}
    
    /* Ajuste para que el contenido no quede tapado por la barra */
    .block-container {{
        padding-bottom: 90px !important; /* Espacio extra abajo */
    }}

    /* Estilo de los Botones de Navegación (Streamlit Buttons hackeados) */
    /* Usamos un selector específico para los botones que pondremos en la barra */
    div[data-testid="stHorizontalBlock"] button {{
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        color: #666 !important;
        font-size: 0.8rem !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100% !important;
    }}
    
    /* Estado Activo (Simulado con lógica Python + CSS condicional si fuera posible, 
       pero aquí dependemos de Primary/Secondary) */
    div[data-testid="stHorizontalBlock"] button:focus {{
        color: #2e7d32 !important;
        outline: none !important;
    }}

    /* Sidebar Ajustado */
    section[data-testid="stSidebar"] {{ min-width: 300px !important; max-width: 320px !important; }}
    
    /* Espaciados Generales */
    .stButton > button {{ min-height: 45px !important; margin-top: 0px !important; }}
    
    /* Pills Verdes */
    div[data-testid="stPills"] span[aria-selected="true"] {{ background-color: #2e7d32 !important; color: white !important; }}
    
    /* Footer Texto (dentro del flujo) */
    .footer-text {{
        text-align: center;
        font-size: 0.8em;
        color: #888;
        margin-top: 20px;
        margin-bottom: 20px;
    }}
    </style>
    """, unsafe_allow_html=True)