import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 
import locations 

from views import auth, inventory, market

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    /* Ocultar enlaces automáticos */
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { min-width: 350px !important; max-width: 350px !important; }
    section[data-testid="stSidebar"] .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    section[data-testid="stSidebar"] hr, 
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] .stButton, 
    section[data-testid="stSidebar"] .stProgress { 
        margin-bottom: 0.5rem !important; margin-top: 0.2rem !important; 
    }
    
    /* Pills y Botones */
    div[data-testid="stPills"] span[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    div[data-testid="stPills"] button[aria-selected="true"] { background-color: #2e7d32 !important; border-color: #2e7d32 !important; color: white !important; }
    button[kind="secondary"] { border-radius: 20px; }
    
    /* Alineación */
    div[data-testid="column"] { text-align: center; }
    div.stButton > button, div.stDownloadButton > button { 
        min-height: 45px !important; 
        height: 45px !important;
        margin-top: 0px !important;
    } 

    /* Estilo Botones Footer (Blancos) */
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
    
    .footer-text {
        text-align: center;
        font-size: 0.8em;
        color: #888;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- MEMORIA DE SESIÓN (ESTADO GLOBAL) ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False
if 'page_canjes' not in st.session_state: st.session_state.page_canjes = 1
if 'page_ventas' not in st.session_state: st.session_state.page_ventas = 1
if 'page_pendientes' not in st.session_state: st.session_state.page_pendientes = 1
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False

# Variables de Navegación Segura
if 'current_country' not in st.session_state: st.session_state.current_country = list(config.ALBUM_PAGES.keys())[0]
if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

# --- MODALES Y DIÁLOGOS ---

@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    st.markdown("""
    **Al continuar, declarás bajo juramento que:**
    1. Sos mayor de 18 años.
    2. Aceptás que las transacciones son responsabilidad exclusiva de los usuarios.
    3. Te comprometés a mantener un trato respetuoso.
    """)
    
    if st.button("✅ Entendido, soy +18", type="primary", width="stretch"):
        st.session_state.barrera_superada = True
        st.rerun()

@st.dialog("📤 Ayuda Carga Masiva (CSV)")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### ¿Cómo cargar tu Excel?
    Para ahorrar tiempo, podés subir un archivo `.csv` con tus figuritas.
    
    **El archivo debe tener estas columnas:**
    1. **num**: El número de la figurita (ej: 10, 150).
    2. **status**: Escribí `tengo` o `repetida`.
    3. **price**: Precio de venta (Poné 0 si es para canje).
    
    *(Tip: Descargá la plantilla, completala y subila)*
    """)

@st.dialog("✏️ Editar Perfil")
def mostrar_editar_perfil(user):
    st.markdown("Actualizá tu ubicación para encontrar gente cerca.")
    
    # Recuperamos valores actuales
    current_prov = user.get('province', list(locations.ARGENTINA.keys())[0])
    current_zone = user.get('zone', '')
    
    try: idx_prov = list(locations.ARGENTINA.keys()).index(current_prov)
    except: idx_prov = 0

    new_prov = st.selectbox("Provincia", list(locations.ARGENTINA.keys()), index=idx_prov)
    
    zones = locations.ARGENTINA[new_prov]
    try: idx_zone = zones.index(current_zone) if current_zone in zones else 0
    except: idx_zone = 0
    
    new_zone = st.selectbox("Zona", zones, index=idx_zone)

    if st.button("💾 Guardar Cambios", type="primary", width="stretch"):
        with utils.spinner_futbolero():
            ok, msg = db.update_profile(user['id'], new_prov, new_zone)
        
        if ok:
            # Actualizamos sesión en caliente
            st.session_state.user['province'] = new_prov
            st.session_state.user['zone'] = new_zone
            st.toast("Perfil actualizado!", icon="✅")
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

@st.dialog("⚠️ Cambios sin guardar")
def confirmar_navegacion(user_id, current_country, target_country):
    st.warning(f"Tenés cambios pendientes en **{current_country}**.")
    st.write("Si cambiás de país ahora, se perderán los datos que no guardaste.")
    
    col1, col2 = st.columns(2)
    
    if col1.button("💾 Guardar y Salir", type="primary"):
        session_key = f"inv_state_{current_country}"
        if session_key in st.session_state:
            state = st.session_state[session_key]
            start, end = config.ALBUM_PAGES[current_country]
            df_repes = pd.DataFrame(state['repes'])
            
            with utils.spinner_futbolero():
                db.save_inventory_positive(user_id, start, end, state['owned'], state['wishlist'], df_repes)
                st.session_state.unsaved_changes = False
                st.session_state.current_country = target_country
                st.rerun()
                
    if col2.button("🗑️ Descartar"):
        st.session_state.unsaved_changes = False
        st.session_state.current_country = target_country
        st.rerun()

# --- DIÁLOGOS DEL FOOTER (TEXTOS COMPLETOS) ---
@st.dialog("📧 Contacto")
def mostrar_contacto():
    st.markdown("""
    ### ¿Necesitás ayuda?
    Estamos para darte una mano con tu colección.
    
    * 📧 **Email:** soporte@figus26.com
    * 📷 **Instagram:** @figus26_oficial
    * 🕒 **Horario:** Lunes a Viernes de 9 a 18hs.
    
    ---
    **Reportar Usuario:**
    Si tuviste un problema, enviá una captura de pantalla al mail indicando el nombre del usuario.
    """)

@st.dialog("❓ Preguntas Frecuentes (FAQ)")
def mostrar_faq():
    with st.expander("¿Es gratis usar la app?"):
        st.write("Sí, podés cargar tu álbum y ver el mercado gratis. Tenés 1 contacto diario gratuito.")
    with st.expander("¿Cómo funciona el Premium?"):
        st.write("Con Premium tenés contactos ilimitados, alertas de Wishlist y aparecés destacado en las búsquedas.")
    with st.expander("¿Qué pasa si un usuario no responde?"):
        st.write("Los tratos se cierran por WhatsApp. Si no responde, podés usar el botón 'Fichaje caído' en la pestaña de Pendientes.")
    with st.expander("¿Cómo cargo mis repetidas?"):
        st.write("Podés hacerlo manualmente en la sección 'Mi Álbum' marcando primero las que tenés y luego seleccionando las repetidas, o usando la Carga Masiva (CSV).")

@st.dialog("⚖️ Términos Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones")
    st.markdown(config.TEXTO_LEGAL_COMPLETO)
    st.divider()
    st.caption("Al usar esta aplicación, aceptás que Figus 26 es solo un intermediario de contacto.")


# ==========================================
#      FLUJO LÓGICO PRINCIPAL
# ==========================================

# 1. BARRERA DE EDAD (BLOQUEANTE)
if not st.session_state.barrera_superada:
    mostrar_barrera_entrada()
    st.stop() # Detiene la ejecución aquí si no acepta

# 2. INICIO DE SESIÓN
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    auth.mostrar_login()
else:
    # --- USUARIO LOGUEADO ---
    user = st.session_state.user
    
    # Cargar contactos desbloqueados si no están en memoria
    if not st.session_state.unlocked_users:
        st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])

    # Chequeo de Reset Diario de Créditos
    if db.verify_daily_reset(user):
        if not user.get('is_premium', False):
            st.toast("📅 ¡Nuevo día! Se renovaron tus créditos.", icon="☀️")

    # Notificaciones Premium (Wishlist Match)
    if user.get('is_premium', False) and 'wishlist_notified' not in st.session_state:
        m_df = db.fetch_market(user['id'])
        matches, ventas = db.find_matches(user['id'], m_df)
        wish_hits = [x for x in matches + ventas if x.get('is_wishlist', False)]
        if wish_hits:
            qty = len(wish_hits)
            st.toast(f"🔔 ¡Atención! Hay {qty} figuritas de tu Wishlist disponibles.", icon="🎉")
        st.session_state.wishlist_notified = True

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.title(f"Hola {user['nick']}")
        st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
        
        # Botón Editar Perfil
        if st.button("✏️ Editar Perfil", key="btn_edit_profile"):
             mostrar_editar_perfil(user)
             
        st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
        
        # Notificaciones de Transacciones Pendientes
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
                        if ok: st.toast("¡Confirmado!"); time.sleep(1); st.rerun()
                        else: st.error(msg)
                    if c2.button("❌ No", key=f"n_{req['id']}", use_container_width=True):
                        db.reject_transaction_request(req['id'])
                        st.rerun()
        
        st.divider()
        
        # Barra de Progreso Global
        start_curr, end_curr = config.ALBUM_PAGES[st.session_state.current_country]
        # Hacemos una query rapida para el total global (aprox)
        _, _, _, df_full = db.get_inventory_status(user['id'], 1, 800) 
        try: tengo_total = df_full[df_full['status'] == 'tengo'].shape[0]
        except: tengo_total = 0
        total_album_glob = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
        
        st.progress(min(tengo_total / total_album_glob, 1.0), text="🏆 Mi Álbum")
        st.caption(f"Tenés **{tengo_total}** de {total_album_glob}.")
        
        # Botón Viralidad (WhatsApp)
        full_wishlist = db.get_full_wishlist(user['id'])
        if full_wishlist:
            link_share = utils.generar_link_whatsapp_wishlist(full_wishlist)
            st.link_button("📢 Compartir Deseados", link_share, type="primary", use_container_width=True)
        
        st.divider()
        
        # Carga Masiva CSV
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
        
        # Sección Premium / Gratis
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
                    
        # Logout
        if st.button("Chau / Salir"): st.session_state.user = None; st.rerun()

    # --- PANTALLA PRINCIPAL ---
    st.header("📖 Mi Álbum")
    
    # Selector de País con Lógica de Intercepción
    paises = list(config.ALBUM_PAGES.keys())
    try: idx_actual = paises.index(st.session_state.current_country)
    except: idx_actual = 0
    
    seleccion_usuario = st.selectbox(
        "Sección:", 
        paises, 
        index=idx_actual,
        key="nav_selection"
    )

    # Detectar cambio de selección
    if seleccion_usuario != st.session_state.current_country:
        if st.session_state.unsaved_changes:
            # Si hay cambios, pedimos confirmación
            confirmar_navegacion(user['id'], st.session_state.current_country, seleccion_usuario)
        else:
            # Si no hay cambios, navegamos directo
            st.session_state.current_country = seleccion_usuario
            st.rerun()

    # Renderizado del Inventario
    start, end = config.ALBUM_PAGES[st.session_state.current_country]
    inventory.render_inventory(user, start, end, st.session_state.current_country)
    
    st.divider()
    
    # Renderizado del Mercado
    market.render_market(user)

    # --- FOOTER ---
    st.divider()
    fc1, fc2, fc3 = st.columns(3)
    if fc1.button("📧 Contacto", width="stretch", type="secondary"): mostrar_contacto()
    if fc2.button("❓ FAQ", width="stretch", type="secondary"): mostrar_faq()
    if fc3.button("⚖️ Legales", width="stretch", type="secondary"): mostrar_legales()
    
    st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)