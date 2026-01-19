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
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# --- CARGAR ESTILOS CSS ---
styles.load_css()

# --- MEMORIA GLOBAL ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False
if 'page_canjes' not in st.session_state: st.session_state.page_canjes = 1
if 'page_ventas' not in st.session_state: st.session_state.page_ventas = 1
if 'page_pendientes' not in st.session_state: st.session_state.page_pendientes = 1
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False

# --- VARIABLES PARA NAVEGACIÓN SEGURA ---
if 'current_country' not in st.session_state: st.session_state.current_country = list(config.ALBUM_PAGES.keys())[0]
if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

# ==========================================
#     FLUJO LÓGICO PRINCIPAL
# ==========================================

# 1. VERIFICAR URL +18
if "over18" in st.query_params: 
    st.session_state.barrera_superada = True

# 2. AUTO-LOGIN (PERSISTENCIA)
if 'user' not in st.session_state or st.session_state.user is None:
    if "token" in st.query_params:
        uid = utils.validar_token_sesion(st.query_params["token"])
        if uid:
            restored_user = db.get_user_by_id(uid)
            if restored_user:
                st.session_state.user = restored_user
                st.session_state.barrera_superada = True

# 3. BARRERA DE EDAD (BLOQUEANTE)
if not st.session_state.barrera_superada:
    modals.mostrar_barrera_entrada() 
    st.stop()

# 4. VERIFICACIÓN DE LOGIN
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    auth.mostrar_login()
else:
    user = st.session_state.user
    
    # --- FLUJO ADMIN ---
    if user.get('is_admin', False):
        with st.sidebar:
            st.title("Admin Panel")
            if st.button("Salir / Logout", use_container_width=True): # <--- CORREGIDO
                st.session_state.user = None
                st.query_params.clear()
                st.rerun()
        admin.render_admin_panel(user)
        
    # --- FLUJO USUARIO NORMAL ---
    else:
        # Inicializaciones
        if not st.session_state.unlocked_users:
            st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])

        if db.verify_daily_reset(user):
            if not user.get('is_premium', False): st.toast("📅 Créditos renovados.", icon="☀️")

        if user.get('is_premium', False) and 'wishlist_notified' not in st.session_state:
            m_df = db.fetch_market(user['id'])
            matches, ventas = db.find_matches(user['id'], m_df)
            wish_hits = [x for x in matches + ventas if x.get('is_wishlist', False)]
            if wish_hits: st.toast(f"🔔 {len(wish_hits)} de tu Wishlist disponibles.", icon="🎉")
            st.session_state.wishlist_notified = True

        # --- SIDEBAR ---
        sidebar.render_user_sidebar(user)

        # --- CONTENIDO PRINCIPAL ---
        st.header("📖 Mi Álbum")
        
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
        
        st.divider()
        market.render_market(user)

        # --- FOOTER ---
        st.divider()
        fc1, fc2, fc3 = st.columns(3)
        # CORREGIDOS: use_container_width=True
        if fc1.button("📧 Contacto", use_container_width=True, type="secondary"): modals.mostrar_contacto()
        if fc2.button("❓ FAQ", use_container_width=True, type="secondary"): modals.mostrar_faq()
        if fc3.button("⚖️ Legales", use_container_width=True, type="secondary"): modals.mostrar_legales()
        
        st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)