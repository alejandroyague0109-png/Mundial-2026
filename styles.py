import streamlit as st

def load_css():
    st.markdown("""
    <style>
    /* =========================================
       1. CONFIGURACIÓN GENERAL Y TIPOGRAFÍA
       Estilo: Oficial, Limpio, Corporativo
    ========================================= */
    
    /* Ocultar elementos decorativos de Streamlit */
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    footer { visibility: hidden; }
    
    /* Fondo y Fuente base */
    .stApp {
        background-color: #ffffff; /* Blanco puro para limpieza */
        font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* =========================================
       2. SIDEBAR (BARRA LATERAL)
    ========================================= */
    section[data-testid="stSidebar"] {
        min-width: 350px !important;
        max-width: 350px !important;
        background-color: #f8f9fa; /* Gris muy suave, institucional */
        border-right: 1px solid #e0e0e0;
    }
    
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }

    /* Ajuste de espaciado en elementos del sidebar para evitar amontonamiento */
    section[data-testid="stSidebar"] hr { margin: 1.5rem 0 !important; }
    section[data-testid="stSidebar"] h1 { font-size: 1.8rem !important; color: #2e7d32; }

    /* =========================================
       3. BOTONES (EL NÚCLEO DEL DISEÑO)
       Geometría: Rectangular, puntas suaves, alto uniforme.
    ========================================= */
    
    /* Selector Global para todos los botones (Button, Download, Link) */
    div.stButton > button, 
    div.stDownloadButton > button,
    div.stLinkButton > a {
        width: 100% !important;             /* Ancho completo siempre */
        min-height: 45px !important;        /* Altura uniforme */
        height: auto !important;
        border-radius: 8px !important;      /* Bordes suavizados (no píldora) */
        font-weight: 600 !important;
        font-size: 16px !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; /* Animación suave */
        box-shadow: none !important;        /* Sin sombras por defecto (Flat) */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin-top: 0px !important;
    }

    /* --- ESTILO SECUNDARIO (POR DEFECTO - NEUTRO/POSITIVO) --- */
    /* Estado Normal: Outline Verde */
    button[kind="secondary"], a[kind="secondary"] {
        background-color: transparent !important;
        border: 2px solid #2e7d32 !important;
        color: #2e7d32 !important;
    }
    
    /* Hover: Sólido Verde */
    button[kind="secondary"]:hover, a[kind="secondary"]:hover {
        background-color: #2e7d32 !important;
        color: #ffffff !important;
        border-color: #2e7d32 !important;
        transform: translateY(-1px); /* Sutil elevación */
    }
    
    /* Active/Click: Verde más oscuro */
    button[kind="secondary"]:active, a[kind="secondary"]:active {
        background-color: #1b5e20 !important;
        border-color: #1b5e20 !important;
        color: white !important;
    }

    /* --- ESTILO PRIMARIO (ACCIÓN CONFIRMADA/ENFÁTICA) --- */
    /* Estado Normal: Sólido Verde */
    button[kind="primary"], a[kind="primary"] {
        background-color: #2e7d32 !important;
        border: 2px solid #2e7d32 !important;
        color: #ffffff !important;
    }
    
    /* Hover: Verde Oscuro */
    button[kind="primary"]:hover, a[kind="primary"]:hover {
        background-color: #1b5e20 !important;
        border-color: #1b5e20 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 6px rgba(46, 125, 50, 0.2) !important;
    }

    /* =========================================
       4. COMPONENTES VARIOS
    ========================================= */
    
    /* Tarjetas (Containers) - Minimalistas */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #e0e0e0 !important; /* Borde muy fino y gris */
        border-radius: 8px !important;
        background-color: #ffffff;
        padding: 1.5rem !important;
        box-shadow: none !important; /* Eliminamos sombras pesadas */
    }

    /* Pills (Selectores de Figus) - Verde Oficial */
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #2e7d32 !important;
        border-color: #2e7d32 !important;
        color: white !important;
        font-weight: bold !important;
    }
    div[data-testid="stPills"] span[aria-selected="false"] {
        background-color: #f1f3f4 !important;
        border-color: #dadce0 !important;
        color: #5f6368 !important;
    }
    
    /* Centrado de columnas */
    div[data-testid="column"] { 
        text-align: center; 
    }

    /* Inputs (Campos de texto) - Sobrios */
    div[data-baseweb="input"] {
        border-radius: 6px !important;
        background-color: #ffffff !important;
        border-color: #e0e0e0 !important;
    }
    
    /* =========================================
       5. CLASES UTILITARIAS (TEXTO)
    ========================================= */
    .footer-text {
        text-align: center;
        font-size: 0.85em;
        color: #9aa0a6;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #f1f3f4;
    }

    /* NOTA: Los botones negativos (Rojos) se manejan mediante inyección local 
       en las vistas (market.py, modals.py) usando selectores específicos, 
       pero heredarán la geometría (border-radius, height) definida aquí. */
    
    </style>
    """, unsafe_allow_html=True)