import streamlit as st

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');

        /* --- CONTENEDORES --- */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            background-color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
            border-color: #00A650;
        }

        /* --- BOTONES: HOMOGENEIZACIÓN (Ghost Style) --- */
        
        /* 1. Botón PRIMARIO (Positivo - Guardar, Confirmar) */
        /* Estado Normal: Blanco con borde Verde */
        div.stButton > button[kind="primary"] {
            background-color: white !important;
            color: #00A650 !important;
            border: 2px solid #00A650 !important;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            transition: all 0.3s ease;
            box-shadow: none;
        }
        /* Hover: Se llena de Verde */
        div.stButton > button[kind="primary"]:hover {
            background-color: #00A650 !important;
            color: white !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0, 166, 80, 0.2);
        }

        /* 2. Botón SECUNDARIO (Neutro - Cancelar, Filtros) */
        /* Estado Normal: Blanco con borde Gris */
        div.stButton > button[kind="secondary"] {
            background-color: white !important;
            color: #555 !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        /* Hover: Se pone Verde (Por defecto acciones neutras/positivas) */
        div.stButton > button[kind="secondary"]:hover {
            border-color: #00A650 !important;
            color: #00A650 !important;
            background-color: #f0fdf4 !important;
        }

        /* --- EXCEPCIONES PARA BOTONES ROJOS (Negativos) --- */
        /* Usaremos una clase CSS inyectada localmente o selectores específicos en las vistas */

        /* --- TIPOGRAFÍA --- */
        h1, h2, h3 { font-family: 'Roboto', sans-serif; color: #1a1a1a; font-weight: 800 !important; }
        
        h1 {
            background: -webkit-linear-gradient(45deg, #1a237e, #0d47a1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* --- PROGRESO --- */
        .stProgress > div > div > div > div {
            background-color: #FFD700;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 2rem !important;
            color: #00A650 !important;
            font-weight: bold !important;
        }
        
        .footer-text {
            text-align: center; color: #888; font-size: 0.85rem;
            margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
        }
        
        [data-testid="stPills"] button { border-radius: 20px !important; }

    </style>
    """, unsafe_allow_html=True)