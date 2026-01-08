import streamlit as st
import config
import database as db
import styles # Nuestro nuevo archivo CSS
from views import auth, inventory, market, layout, sidebar # Nuestros módulos nuevos

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")
styles.load_css() # Cargamos el estilo

# --- MEMORIA GLOBAL ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False
if 'current_country' not in st.session_state: st.session_state.current_country = list(config.ALBUM_PAGES.keys())[0]
if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

# --- 1. BARRERA DE EDAD (BLOQUEANTE) ---
if not st.session_state.barrera_superada:
    layout.mostrar_barrera_entrada()
    st.stop() 

# --- 2. LOGICA DE USUARIO ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    auth.mostrar_login()
else:
    user = st.session_state.user
    
    # Init datos usuario
    if not st.session_state.unlocked_users:
        st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])
    
    if db.verify_daily_reset(user) and not user.get('is_premium', False):
        st.toast("📅 ¡Nuevo día! Se renovaron tus créditos.", icon="☀️")

    # Notif. Wishlist
    if user.get('is_premium', False) and 'wishlist_notified' not in st.session_state:
        m_df = db.fetch_market(user['id'])
        matches, ventas = db.find_matches(user['id'], m_df)
        wish_hits = [x for x in matches + ventas if x.get('is_wishlist', False)]
        if wish_hits: st.toast(f"🔔 {len(wish_hits)} de tu Wishlist disponibles.", icon="🎉")
        st.session_state.wishlist_notified = True

    # --- 3. SIDEBAR (MODULARIZADO) ---
    sidebar.render_sidebar(user)

    # --- 4. CUERPO PRINCIPAL ---
    st.header("📖 Mi Álbum")
    
    # Navegación
    paises = list(config.ALBUM_PAGES.keys())
    try: idx_actual = paises.index(st.session_state.current_country)
    except: idx_actual = 0
    
    seleccion_usuario = st.selectbox("Sección:", paises, index=idx_actual, key="nav_selection")

    if seleccion_usuario != st.session_state.current_country:
        if st.session_state.unsaved_changes:
            layout.confirmar_navegacion(user['id'], st.session_state.current_country, seleccion_usuario)
        else:
            st.session_state.current_country = seleccion_usuario; st.rerun()

    start, end = config.ALBUM_PAGES[st.session_state.current_country]
    inventory.render_inventory(user, start, end, st.session_state.current_country)
    
    st.divider()
    market.render_market(user)

    # --- 5. FOOTER (MODULARIZADO) ---
    layout.render_footer()