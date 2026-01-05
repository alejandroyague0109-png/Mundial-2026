import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 

# Importamos las vistas
from views import auth, inventory, market

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    section[data-testid="stSidebar"] { min-width: 350px !important; max-width: 350px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    div[data-testid="stPills"] span[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    div[data-testid="stPills"] button[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    button[kind="secondary"] { border-radius: 20px; }
    div[data-testid="column"] { text-align: center; }
    div.stButton > button:first-child { min-height: 0px; padding-top: 0px; padding-bottom: 0px; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR MEMORIA GLOBAL ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False
if 'page_canjes' not in st.session_state: st.session_state.page_canjes = 1
if 'page_ventas' not in st.session_state: st.session_state.page_ventas = 1
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False

# --- MODAL BIENVENIDA (TEXTO CORREGIDO) ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    
    # TEXTO RECUPERADO COMPLETO:
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    
    st.markdown("**Al continuar, declarás bajo juramento que sos mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", use_container_width=True):
        st.session_state.barrera_superada = True
        st.rerun()

# --- MODAL AYUDA CSV ---
@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### Formato del Archivo
    Debe tener 3 columnas obligatorias:
    1. **num**: Número de la figurita.
    2. **status**: `tengo` o `repetida`.
    3. **price**: Precio de venta (0 si es para canje).
    """)

# --- LOGIC FLOW ---

# 1. Barrera de Edad
if not st.session_state.barrera_superada:
    mostrar_barrera_entrada()

# 2. Control de Sesión
if 'user' not in st.session_state: st.session_state.user = None

# 3. Router de Vistas
if not st.session_state.user:
    # VISTA DE LOGIN
    auth.mostrar_login()
else:
    # VISTA PRINCIPAL (LOGUEADO)
    user = st.session_state.user
    
    # Check diario
    if db.verify_daily_reset(user):
        st.session_state.unlocked_users = set()
        st.toast("📅 ¡Nuevo día! Se renovaron tus créditos.", icon="☀️")

    # Cálculos globales para Sidebar
    seleccion_pais = st.session_state.get("seleccion_pais_key", list(config.ALBUM_PAGES.keys())[0])
    start, end = config.ALBUM_PAGES[seleccion_pais]
    total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
    
    # Obtener totales para barra de progreso
    _, _, df_full = db.get_inventory_status(user['id'], start, end)
    try: tengo_total = df_full[df_full['status'] == 'tengo'].shape[0]
    except: tengo_total = 0
    
    # SIDEBAR
    with st.sidebar:
        st.title(f"Hola {user['nick']}")
        st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
        st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
        
        st.divider()
        st.progress(min(tengo_total / total_album, 1.0), text="🏆 Mi Álbum")
        st.caption(f"Tenés **{tengo_total}** de {total_album}.")
        
        st.divider()
        with st.expander("📤 Carga Masiva (CSV)"):
            col_a, col_b = st.columns(2)
            if col_a.button("❓ Ayuda"): mostrar_instrucciones_csv()
            df_plantilla = pd.DataFrame([{"num": 10, "status": "tengo", "price": 0}, {"num": 25, "status": "repetida", "price": 500}])
            col_b.download_button("⬇️ Plantilla", df_plantilla.to_csv(index=False).encode('utf-8'), "plantilla.csv", "text/csv")
            up = st.file_uploader("Subí tu CSV", type="csv")
            if up and st.button("🚀 Procesar", type="primary"):
                with utils.spinner_futbolero():
                    ok, msg = db.process_csv_upload(pd.read_csv(up), user['id'])
                if ok: st.toast("¡Cargado!", icon="📦"); st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)
                
        st.divider()
        
        if user.get('is_premium', False): 
            st.success("💎 PREMIUM")
        else:
            st.info("👤 GRATIS")
            
            contacts = user.get('daily_contacts_count', 0)
            if contacts >= 1: 
                st.progress(1.0, text="Límite: 1/1 (Agotado)")
            else: 
                st.progress(0.0, text="Límite: 0/1 (Disponible)")
            
            if st.button("💎 Hacete Premium", use_container_width=True): 
                market.mostrar_modal_premium()
            
            with st.expander("Validar Pago"):
                op = st.text_input("ID Op")
                if op and st.button("Validar"):
                    with utils.spinner_futbolero():
                        ok, msg = db.verificar_pago_mp(op, user['id'])
                    if ok: st.toast("¡Premium!", icon="💎"); st.rerun()
                    else: st.error(msg)
                    
        if st.button("Chau / Salir"): st.session_state.user = None; st.rerun()

    # APP PRINCIPAL
    st.selectbox("Sección:", list(config.ALBUM_PAGES.keys()), key="seleccion_pais_key")
    
    # 1. Renderizar Inventario
    inventory.render_inventory(user, start, end, seleccion_pais)
    
    st.divider()
    
    # 2. Renderizar Mercado
    market.render_market(user)