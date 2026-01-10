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

        /* --- BOTONES: GHOST STYLE --- */
        
        /* 1. PRIMARIO (Verde) */
        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"],
        div.stLinkButton > a[kind="primary"] {
            background-color: white !important;
            color: #00A650 !important;
            border: 2px solid #00A650 !important;
            border-radius: 8px;
            font-weight: bold;
            text-transform: uppercase;
            transition: all 0.3s ease;
            box-shadow: none;
            text-decoration: none !important; /* Para links */
        }
        div.stButton > button[kind="primary"]:hover,
        div.stDownloadButton > button[kind="primary"]:hover,
        div.stLinkButton > a[kind="primary"]:hover {
            background-color: #00A650 !important;
            color: white !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0, 166, 80, 0.2);
        }

        /* 2. SECUNDARIO (Neutro/Gris) */
        div.stButton > button[kind="secondary"], 
        div.stDownloadButton > button[kind="secondary"],
        div.stLinkButton > a[kind="secondary"] {
            background-color: white !important;
            color: #555 !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none !important;
        }
        div.stButton > button[kind="secondary"]:hover,
        div.stDownloadButton > button[kind="secondary"]:hover,
        div.stLinkButton > a[kind="secondary"]:hover {
            border-color: #00A650 !important;
            color: #00A650 !important;
            background-color: #f0fdf4 !important;
        }

        /* --- ESTILO ESPECIAL: FILE UPLOADER (Browse files) --- */
        /* Forzamos al botón interno del uploader a parecerse al Primary */
        [data-testid="stFileUploader"] button {
            background-color: white !important;
            color: #00A650 !important;
            border: 2px solid #00A650 !important;
            font-weight: bold;
        }
        [data-testid="stFileUploader"] button:hover {
            background-color: #00A650 !important;
            color: white !important;
        }

        /* --- TIPOGRAFÍA Y OTROS --- */
        h1, h2, h3 { font-family: 'Roboto', sans-serif; color: #1a1a1a; font-weight: 800 !important; }
        
        h1 {
            background: -webkit-linear-gradient(45deg, #1a237e, #0d47a1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stProgress > div > div > div > div { background-color: #FFD700; }
        
        [data-testid="stMetricValue"] {
            font-size: 2rem !important; color: #00A650 !important; font-weight: bold !important;
        }
        
        .footer-text {
            text-align: center; color: #888; font-size: 0.85rem;
            margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;
        }
        
        [data-testid="stPills"] button { border-radius: 20px !important; }

    </style>
    """, unsafe_allow_html=True)