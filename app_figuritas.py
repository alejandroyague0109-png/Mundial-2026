import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 
import locations 
import styles 

# IMPORTAMOS LOS MÓDULOS DE VISTA
from views import auth, inventory, market, admin, sidebar, modals

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26", layout="wide", page_icon="⚽", initial_sidebar_state="collapsed")

# --- CARGAR ESTILOS CSS ---
styles.load_css()

# --- MEMORIA GLOBAL ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False
if 'page_canjes' not in st.session_state: st.session_state.page_canjes = 1
if 'page_ventas' not in st.session_state: st.session_state.page_ventas = 1
if 'page_pendientes' not in st.session_state: st.session_state.page_pendientes = 1
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False

# --- VARIABLES DE NAVEGACIÓN (ROUTER) ---
if 'current_view' not in st.session_state: st.session_state.current_view = 'album' # 'album' o 'mercado'
if 'current_country' not in st.session_state: st.session_state.current_country = list(config.ALBUM_PAGES.keys())[0]
if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

# ==========================================
#      FLUJO LÓGICO PRINCIPAL
# ==========================================

# 1. VERIFICAR URL +18 / TOKEN
if "over18" in st.query_params: st.session_state.barrera_superada = True

if 'user' not in st.session_state or st.session_state.user is None:
    if "token" in st.query_params:
        uid = utils.validar_token_sesion(st.query_params["token"])
        if uid:
            restored_user = db.get_user_by_id(uid)
            if restored_user:
                st.session_state.user = restored_user
                st.session_state.barrera_superada = True

# 2. BARRERA DE EDAD
if not st.session_state.barrera_superada:
    modals.mostrar_barrera_entrada() 
    st.stop()

# 3. VERIFICACIÓN DE LOGIN
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    auth.mostrar_login()
else:
    user = st.session_state.user
    
    # --- ADMIN PANEL ---
    if user.get('is_admin', False):
        with st.sidebar:
            st.title("Admin")
            if st.button("Salir", use_container_width=True):
                st.session_state.user = None; st.query_params.clear(); st.rerun()
        admin.render_admin_panel(user)
        
    # --- USUARIO NORMAL (APP MÓVIL) ---
    else:
        # Inicializaciones silenciosas
        if not st.session_state.unlocked_users:
            st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])
        db.verify_daily_reset(user)

        # --- SIDEBAR (SIEMPRE DISPONIBLE) ---
        sidebar.render_user_sidebar(user)

        # --- BARRA DE NAVEGACIÓN (TIPO APP) ---
        # Usamos columnas para simular tabs. 
        # Al tocar un botón, cambiamos el estado 'current_view' y hacemos rerun.
        
        nav_c1, nav_c2 = st.columns(2)
        
        # Estilo visual: Botón Primary = Activo, Secondary = Inactivo
        tipo_album = "primary" if st.session_state.current_view == 'album' else "secondary"
        tipo_mercado = "primary" if st.session_state.current_view == 'mercado' else "secondary"
        
        # [MODIFICACIÓN] Chequeo de cambios sin guardar antes de cambiar de sección
        if nav_c1.button("📖 MI ÁLBUM", type=tipo_album, use_container_width=True):
            if st.session_state.current_view != 'album':
                if st.session_state.unsaved_changes:
                    modals.confirmar_cambio_seccion('album', user)
                else:
                    st.session_state.current_view = 'album'
                    st.rerun()
            
        if nav_c2.button("🔍 MERCADO", type=tipo_mercado, use_container_width=True):
            if st.session_state.current_view != 'mercado':
                if st.session_state.unsaved_changes:
                    modals.confirmar_cambio_seccion('mercado', user)
                else:
                    st.session_state.current_view = 'mercado'
                    st.rerun()
        
        st.divider()

        # --- ROUTER DE VISTAS ---
        if st.session_state.current_view == 'album':
            # VISTA: ÁLBUM
            # Selector de País
            paises = list(config.ALBUM_PAGES.keys())
            try: idx = paises.index(st.session_state.current_country)
            except: idx = 0
            
            nuevo_pais = st.selectbox("Sección:", paises, index=idx, key="nav_pais_selector")
            
            if nuevo_pais != st.session_state.current_country:
                if st.session_state.unsaved_changes:
                    modals.confirmar_cambio_pais(nuevo_pais, user)
                else:
                    st.session_state.current_country = nuevo_pais
                    st.rerun()
            
            start, end = config.ALBUM_PAGES[st.session_state.current_country]
            inventory.render_inventory(user, start, end, st.session_state.current_country)

        elif st.session_state.current_view == 'mercado':
            # VISTA: MERCADO
            market.render_market(user)

        # --- FOOTER (CONTACTO / LEGALES) ---
        # Se muestra al final de cualquiera de las dos vistas
        st.markdown("<br><br>", unsafe_allow_html=True) # Espacio extra
        st.divider()
        fc1, fc2, fc3 = st.columns(3)
        if fc1.button("📧 Contacto", use_container_width=True, type="secondary"): modals.mostrar_contacto()
        if fc2.button("❓ FAQ", use_container_width=True, type="secondary"): modals.mostrar_faq()
        if fc3.button("⚖️ Legales", use_container_width=True, type="secondary"): modals.mostrar_legales()
        
        st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)