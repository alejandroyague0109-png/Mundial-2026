import streamlit as st

def load_css():
    st.markdown("""
    <style>
    /* =========================================
       1. IDENTIDAD VISUAL WC26 - CONFIGURACIÓN BASE
    ========================================= */
    
    /* Importación de fuentes (opcional, usamos sistemas safe-fonts por rendimiento) */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700;900&display=swap');

    /* Ocultar elementos decorativos default de Streamlit */
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    footer { visibility: hidden; }
    
    /* Fondo Blanco Puro */
    .stApp {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-family: "Roboto", "Arial", sans-serif;
    }

    /* --- DECORACIÓN SUPERIOR (HEADER GRADIENT) --- */
    /* Simula el borde multicolor del álbum */
    div[data-testid="stAppViewContainer"]::before {
        content: "";
        display: block;
        height: 6px;
        width: 100%;
        position: fixed;
        top: 0;
        left: 0;
        z-index: 999999;
        background: linear-gradient(90deg, 
            #FF1744 0%, 
            #FF9100 20%, 
            #C6FF00 40%, 
            #00E676 60%, 
            #2979FF 80%, 
            #651FFF 100%);
    }

    /* =========================================
       2. TIPOGRAFÍA (ESTILO '26')
    ========================================= */
    
    /* Títulos masivos, negros y en mayúsculas */
    h1, h2, h3 {
        font-family: "Arial Black", "Roboto Black", "Arial", sans-serif !important;
        font-weight: 900 !important;
        text-transform: uppercase !important;
        color: #000000 !important;
        letter-spacing: -1px !important; /* Tracking apretado estilo logo */
        margin-bottom: 1rem !important;
    }
    
    /* Ajuste específico para H1 */
    h1 {
        font-size: 2.5rem !important;
        border-bottom: 3px solid #000000; /* Subrayado grueso negro */
        padding-bottom: 10px;
        display: inline-block;
    }

    /* =========================================
       3. SIDEBAR (BARRA LATERAL)
    ========================================= */
    section[data-testid="stSidebar"] {
        background-color: #FAFAFA !important; /* Gris casi blanco */
        border-right: 1px solid #E0E0E0;
    }
    
    /* Título del sidebar */
    section[data-testid="stSidebar"] h1 {
        font-size: 1.8rem !important;
        border-bottom: none !important;
        color: #000000 !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    /* =========================================
       4. BOTONES (HOMOGENEIDAD ESTRICTA)
    ========================================= */
    
    /* GEOMETRÍA BASE PARA TODOS LOS BOTONES 
       Esto asegura que el botón "Guardar" y "Cancelar" midan lo mismo.
    */
    div.stButton > button, 
    div.stDownloadButton > button,
    div.stLinkButton > a {
        width: 100% !important;             /* Ancho completo */
        min-height: 50px !important;        /* Altura obligatoria */
        height: auto !important;
        border-radius: 4px !important;      /* Borde apenas redondeado */
        font-weight: 800 !important;        /* Texto grueso */
        font-size: 16px !important;
        text-transform: uppercase !important;
        border: none !important;
        box-shadow: none !important;        /* Flat design */
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease-in-out !important;
        margin-top: 0px !important;
    }

    /* --- TIPO PRIMARY (VERDE LIMA + TEXTO NEGRO) --- */
    /* Usado para acciones principales */
    button[kind="primary"], a[kind="primary"] {
        background-color: #C6FF00 !important; /* Verde Lima Vibrante */
        border: 2px solid #C6FF00 !important;
        color: #000000 !important;            /* Texto Negro para contraste */
    }
    
    /* Hover Primary */
    button[kind="primary"]:hover, a[kind="primary"]:hover {
        background-color: #AEEA00 !important; /* Un poco más oscuro */
        border-color: #AEEA00 !important;
        color: #000000 !important;
        transform: translateY(-2px);
    }

    /* --- TIPO SECONDARY (OUTLINE O BLANCO) --- */
    /* Usado por defecto */
    button[kind="secondary"], a[kind="secondary"] {
        background-color: #FFFFFF !important;
        border: 2px solid #E0E0E0 !important; /* Gris suave */
        color: #000000 !important;
    }
    
    /* Hover Secondary -> Se vuelve Verde */
    button[kind="secondary"]:hover, a[kind="secondary"]:hover {
        border-color: #C6FF00 !important;
        background-color: #FAFAFA !important;
        color: #000000 !important;
    }

    /* --- BOTONES NEGATIVOS (ESTILO BASE PARA INYECCIONES) --- */
    /* Nota: Las inyecciones locales en market.py/inventory.py usarán 
       selectores específicos, pero heredarán la geometría de arriba (50px height).
       Aquí definimos una clase de utilidad si hiciera falta, aunque Streamlit
       usa estilos inline para overriding.
    */

    /* =========================================
       5. COMPONENTES Y TARJETAS
    ========================================= */
    
    /* Tarjetas (Containers) - Estilo Flat */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #E0E0E0 !important; /* Borde fino gris */
        border-radius: 4px !important;
        background-color: #FFFFFF !important;
        padding: 1.5rem !important;
        box-shadow: none !important;
    }
    
    /* Expander (Acordeones) */
    .streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-bottom: 1px solid #F0F0F0;
    }

    /* Pills (Selectores) - Verde Lima */
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #C6FF00 !important;
        border-color: #C6FF00 !important;
        color: #000000 !important; /* Texto negro */
        font-weight: 800 !important;
    }
    div[data-testid="stPills"] span[aria-selected="false"] {
        background-color: #F5F5F5 !important;
        border-color: #E0E0E0 !important;
        color: #666666 !important;
    }

    /* Inputs y Selectbox */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border-color: #CCCCCC !important;
        border-radius: 4px !important;
    }

    /* Progress Bar - Colores del mundial */
    div[data-testid="stProgress"] > div > div {
        background: linear-gradient(90deg, #C6FF00, #2979FF);
    }

    /* Footer Text */
    .footer-text {
        text-align: center;
        font-size: 0.8rem;
        color: #9E9E9E;
        margin-top: 3rem;
        border-top: 1px solid #EEEEEE;
        padding-top: 1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    </style>
    """, unsafe_allow_html=True)