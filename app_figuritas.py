import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 

from views import auth, inventory, market

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    /* Ocultar enlaces de títulos */
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    
    /* Sidebar Ajustado */
    section[data-testid="stSidebar"] { min-width: 350px !important; max-width: 350px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    
    /* Espaciados */
    section[data-testid="stSidebar"] hr, 
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] .stButton, 
    section[data-testid="stSidebar"] .stProgress { 
        margin-bottom: 0.5rem !important; margin-top: 0.2rem !important; 
    }
    section[data-testid="stSidebar"] h1 { font-size: 2rem !important; padding-bottom: 0.5rem !important; }
    
    /* Pills Verdes */
    div[data-testid="stPills"] span[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    div[data-testid="stPills"] button[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    
    /* Botones Redondeados */
    button[kind="secondary"] { border-radius: 20px; }
    
    /* Centrar Paginación */
    div[data-testid="column"] { text-align: center; }

    /* Corrección altura botones */
    div.stButton > button, div.stDownloadButton > button { 
        min-height: 45px !important; 
        height: 45px !important;
        margin-top: 0px !important;
    } 

    /* Botón WhatsApp Blanco */
    a[kind="secondary"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
        text-decoration: none !important;
    }
    a[kind="secondary"]:hover {
        background-color: #f0f0f0 !important;
        border-color: #999999 !important;
        color: #000000 !important;
    }
    
    /* Estilo Footer */
    .footer-text {
        text-align: center;
        font-size: 0.8em;
        color: #888;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- MEMORIA ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False
if 'page_canjes' not in st.session_state: st.session_state.page_canjes = 1
if 'page_ventas' not in st.session_state: st.session_state.page_ventas = 1
if 'page_pendientes' not in st.session_state: st.session_state.page_pendientes = 1
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False

# --- MODALES ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    st.markdown("**Al continuar, declarás bajo juramento que sos mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", width="stretch"):
        st.session_state.barrera_superada = True
        st.rerun()

@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### Formato del Archivo
    Debe tener 3 columnas obligatorias:
    1. **num**: Número de la figurita (ej: 10, 150).
    2. **status**: Escribí `tengo` o `repetida`.
    3. **price**: Precio de venta (0 si es para canje).
    *(Opcional: 'quantity')*
    """)

# --- FUNCIONES POPUP FOOTER (NUEVAS) ---
@st.dialog("📧 Contacto")
def mostrar_contacto():
    st.markdown("""
    ### ¿Necesitás ayuda?
    Estamos para darte una mano con tu colección.
    
    * 📧 **Email:** soporte@figus26.com
    * 📷 **Instagram:** @figus26_oficial
    * 🕒 **Horario:** Lunes a Viernes de 9 a 18hs.
    """)
    st.info("Si tuviste un problema con un usuario, por favor reportalo enviando una captura de pantalla al mail.")

@st.dialog("❓ Preguntas Frecuentes (FAQ)")
def mostrar_faq():
    with st.expander("¿Es gratis usar la app?"):
        st.write("Sí, podés cargar tu álbum y ver el mercado gratis. Tenés 1 contacto diario gratuito.")
    with st.expander("¿Cómo funciona el Premium?"):
        st.write("Con Premium tenés contactos ilimitados, alertas de Wishlist y aparecés destacado en las búsquedas.")
    with st.expander("¿Qué pasa si un usuario no responde?"):
        st.write("Los tratos se cierran por WhatsApp. Si no responde, podés 'Ocultar' la negociación en la pestaña de Pendientes.")
    with st.expander("¿Cómo cargo mis repetidas?"):
        st.write("Podés hacerlo manualmente en la sección 'Mi Álbum' seleccionando las figus y luego 'Repes', o usando la Carga Masiva (CSV) en el menú lateral.")

@st.dialog("⚖️ Términos Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones")
    st.markdown(config.TEXTO_LEGAL_COMPLETO)
    st.divider()
    st.caption("Al usar esta aplicación, aceptás que Figus 26 es solo un intermediario de contacto y no se responsabiliza por las transacciones físicas o monetarias entre usuarios.")

# --- FLUJO LÓGICO ---
if not st.session_state.barrera_superada:
    mostrar_barrera_entrada()

if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    auth.mostrar_login()
else:
    user = st.session_state.user
    
    if not st.session_state.unlocked_users:
        st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])

    if db.verify_daily_reset(user):
        if not user.get('is_premium', False):
            st.toast("📅 ¡Nuevo día! Se renovaron tus créditos.", icon="☀️")

    # Notificaciones Premium Wishlist
    if user.get('is_premium', False) and 'wishlist_notified' not in st.session_state:
        m_df = db.fetch_market(user['id'])
        matches, ventas = db.find_matches(user['id'], m_df)
        wish_hits = [x for x in matches + ventas if x.get('is_wishlist', False)]
        if wish_hits:
            qty = len(wish_hits)
            st.toast(f"🔔 ¡Atención! Hay {qty} figuritas de tu Wishlist disponibles.", icon="🎉")
        st.session_state.wishlist_notified = True

    seleccion_pais = st.session_state.get("seleccion_pais_key", list(config.ALBUM_PAGES.keys())[0])
    start, end = config.ALBUM_PAGES[seleccion_pais]
    total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
    
    _, _, _, df_full = db.get_inventory_status(user['id'], start, end)
    try: tengo_total = df_full[df_full['status'] == 'tengo'].shape[0]
    except: tengo_total = 0
    
    with st.sidebar:
        st.title(f"Hola {user['nick']}")
        st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
        st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
        
        pending_requests = db.get_pending_transactions(user['id'])
        if pending_requests:
            st.divider()
            st.warning(f"🔔 Tenés {len(pending_requests)} confirmaciones")
            for req in pending_requests:
                with st.expander(f"De {req['users']['nick']}", expanded=True):
                    if req['type'] == 'exchange':
                        st.caption(f"Te dio la **#{req['fig_sent']}** y vos la **#{req['fig_received']}**")
                    else:
                        st.caption(f"Te compró la **#{req['fig_received']}**")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Sí", key=f"y_{req['id']}", use_container_width=True):
                        ok, msg = db.confirm_transaction_request(req['id'], user['id'])
                        if ok: st.toast("¡Confirmado! Inventario actualizado."); time.sleep(1); st.rerun()
                        else: st.error(msg)
                    if c2.button("❌ No", key=f"n_{req['id']}", use_container_width=True):
                        db.reject_transaction_request(req['id'])
                        st.rerun()
        
        st.divider()
        st.progress(min(tengo_total / total_album, 1.0), text="🏆 Mi Álbum")
        st.caption(f"Tenés **{tengo_total}** de {total_album}.")
        st.divider()
        with st.expander("📤 Carga Masiva (CSV)"):
            col_a, col_b = st.columns(2)
            if col_a.button("❓ Ayuda", width="stretch"): mostrar_instrucciones_csv()
            df_plantilla = pd.DataFrame([{"num": 10, "status": "tengo", "price": 0}, {"num": 25, "status": "repetida", "price": 500}])
            col_b.download_button("⬇️ Plantilla", df_plantilla.to_csv(index=False).encode('utf-8'), "plantilla.csv", "text/csv", width="stretch")
            up = st.file_uploader("Subí tu CSV", type="csv")
            if up and st.button("🚀 Procesar", type="primary", width="stretch"):
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
            if contacts >= 1: st.progress(1.0, text="Límite: 1/1 (Agotado)")
            else: st.progress(0.0, text="Límite: 0/1 (Disponible)")
            
            if st.button("💎 Hacete Premium", width="stretch"): 
                market.mostrar_modal_premium()
            
            with st.expander("Validar Pago"):
                op = st.text_input("ID Op")
                if op and st.button("Validar"):
                    with utils.spinner_futbolero():
                        ok, msg = db.verificar_pago_mp(op, user['id'])
                    if ok: st.toast("¡Premium!", icon="💎"); st.rerun()
                    else: st.error(msg)
        if st.button("Chau / Salir"): st.session_state.user = None; st.rerun()

    st.header("📖 Mi Álbum")
    st.selectbox("Sección:", list(config.ALBUM_PAGES.keys()), key="seleccion_pais_key")
    inventory.render_inventory(user, start, end, seleccion_pais)
    st.divider()
    market.render_market(user)

    # --- FOOTER (NUEVO) ---
    st.divider()
    fc1, fc2, fc3 = st.columns(3)
    
    # Usamos type="secondary" (fondo blanco) para que no compitan visualmente
    if fc1.button("📧 Contacto", width="stretch", type="secondary"): mostrar_contacto()
    if fc2.button("❓ FAQ", width="stretch", type="secondary"): mostrar_faq()
    if fc3.button("⚖️ Legales", width="stretch", type="secondary"): mostrar_legales()
    
    st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)