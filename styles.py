import streamlit as st

def load_css():
    st.markdown("""
    <style>
        /* --- FUENTES E IMPORTACIONES --- */
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

        /* --- CONTENEDORES Y TARJETAS --- */
        /* Darle sombra y bordes suaves a los containers (las cartas de jugadores) */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            border-color: #00A650; /* Borde verde al pasar el mouse */
        }

        /* --- BOTONES --- */
        /* Botón Primario (Verde - Acciones Positivas) */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #00C853 0%, #00A650 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        div.stButton > button[kind="primary"]:hover {
            background: linear-gradient(180deg, #00E676 0%, #00C853 100%);
            transform: scale(1.02);
        }

        /* Botón Secundario (Gris/Blanco - Acciones Neutras) */
        div.stButton > button[kind="secondary"] {
            border: 2px solid #e0e0e0;
            color: #333;
            border-radius: 8px;
            font-weight: 600;
        }
        div.stButton > button[kind="secondary"]:hover {
            border-color: #00A650;
            color: #00A650;
        }

        /* --- TÍTULOS Y ENCABEZADOS --- */
        h1, h2, h3 {
            font-family: 'Roboto', sans-serif;
            color: #1a1a1a;
            font-weight: 800 !important;
        }
        
        /* Título Principal con toque dorado/azul */
        h1 {
            background: -webkit-linear-gradient(45deg, #1a237e, #0d47a1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* --- BARRA DE PROGRESO --- */
        .stProgress > div > div > div > div {
            background-color: #FFD700; /* Dorado Copa del Mundo */
            background-image: linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent);
            background-size: 1rem 1rem;
        }

        /* --- SIDEBAR --- */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #eee;
        }

        /* --- METRICS (Números grandes) --- */
        [data-testid="stMetricValue"] {
            font-size: 2rem !important;
            color: #00A650 !important; /* Verde */
            font-weight: bold !important;
        }

        /* --- FOOTER --- */
        .footer-text {
            text-align: center;
            color: #888;
            font-size: 0.85rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        
        /* --- PILLS (Selectores) --- */
        /* Ajuste para que se vean como botones de táctica */
        [data-testid="stPills"] button {
            border-radius: 20px !important;
        }

    </style>
    """, unsafe_allow_html=True)