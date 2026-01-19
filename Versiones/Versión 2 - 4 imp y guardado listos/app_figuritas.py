import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 
import locations 

# IMPORTAMOS EL NUEVO MÓDULO ADMIN
from views import auth, inventory, market, admin 

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

    /* Botón WhatsApp/Footer Blanco */
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
    
    /* Footer Texto */
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

# --- NUEVAS VARIABLES PARA NAVEGACIÓN SEGURA ---
if 'current_country' not in st.session_state: st.session_state.current_country = list(config.ALBUM_PAGES.keys())[0]
if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

# --- MODALES ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    st.markdown("**Al continuar, declarás bajo juramento que sos mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", width="stretch"):
        st.session_state.barrera_superada = True
        # FIX: Guardamos en la URL para que persista al recargar
        st.query_params["over18"] = "true"
        st.rerun()

# --- NUEVO MODAL DE NAVEGACIÓN SEGURA (CORREGIDO Y BLINDADO) ---
@st.dialog("⚠️ Cambios sin guardar")
def confirmar_cambio_pais(target_pais, user):
    st.write(f"Tenés cambios pendientes en **{st.session_state.current_country}**.")
    st.warning("¿Querés guardar antes de salir?")
    
    col1, col2 = st.columns(2)
    
    # Opción 1: Guardar y Continuar
    if col1.button("💾 Guardar y Continuar", type="primary", width="stretch"):
        curr = st.session_state.current_country
        s, e = config.ALBUM_PAGES[curr]
        
        # 1. Recuperamos datos de Pills (Tengo / Wishlist)
        tengo_data = st.session_state.get(f"pills_tengo_{curr}", [])
        wish_data = st.session_state.get(f"pills_wish_{curr}", [])
        
        # 2. RECONSTRUCCIÓN DE LA TABLA DE REPETIDAS (Lógica Robusta)
        # Paso A: Obtenemos los IDs seleccionados actualmente
        repes_ids = st.session_state.get(f"repes_{curr}", [])
        
        # Paso B: Consultamos la DB para obtener los valores originales (Precio/Modo)
        # Esto evita que si una fila NO fue editada, se sobrescriba con defaults (0/Canje)
        _, _, repes_info_db, _ = db.get_inventory_status(user['id'], s, e)
        
        # Paso C: Creamos el DataFrame Base con la info de la DB
        data_base = []
        for r in repes_ids:
            info = repes_info_db.get(r, {})
            p = info.get('price', 0)
            q = info.get('quantity', 1)
            m = "💰 Venta" if p > 0 else "🔄 Canje"
            data_base.append({"Figurita": r, "Cantidad": q, "Modo": m, "Precio": p})
        
        df_repes = pd.DataFrame(data_base)
        
        # Paso D: APLICAMOS LOS CAMBIOS PENDIENTES (DELTAS)
        # Leemos el estado interno del editor para ver qué modificó el usuario antes de cambiar de pag
        editor_val = st.session_state.get(f"editor_{curr}")
        
        if editor_val and isinstance(editor_val, dict) and "edited_rows" in editor_val:
            # Iteramos sobre las filas editadas y actualizamos el DataFrame Base
            for idx_str, changes in editor_val["edited_rows"].items():
                idx = int(idx_str)
                if idx < len(df_repes):
                    for c, v in changes.items():
                        df_repes.at[idx, c] = v
        
        # 3. Guardamos en DB
        with utils.spinner_futbolero():
             db.save_inventory_positive(user['id'], s, e, tengo_data, wish_data, df_repes)
        
        # 4. Navegamos
        st.session_state.unsaved_changes = False
        st.session_state.current_country = target_pais
        st.rerun()
        
    # Opción 2: Descartar
    if col2.button("🗑️ Descartar Cambios", width="stretch"):
        st.session_state.unsaved_changes = False
        st.session_state.current_country = target_pais
        st.rerun()

@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### Formato del Archivo
    Debe tener 3 columnas obligatorias:
    1. **num**: Número de la figurita.
    2. **status**: `tengo` o `repetida`.
    3. **price**: Precio (0 si es canje).
    """)

# --- DIALOGO EDITAR PERFIL ---
@st.dialog("✏️ Editar Perfil")
def mostrar_editar_perfil(user):
    st.markdown("Actualizá tu ubicación para encontrar gente cerca.")
    
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
            st.session_state.user['province'] = new_prov
            st.session_state.user['zone'] = new_zone
            st.toast("Perfil actualizado!", icon="✅")
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

# --- POPUPS FOOTER ---
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
        st.write("Los tratos se cierran por WhatsApp. Si no responde, podés 'Fichaje caído' en la pestaña de Pendientes para sacarlo de tu lista.")
    with st.expander("¿Cómo cargo mis repetidas?"):
        st.write("Podés hacerlo manualmente en la sección 'Mi Álbum' seleccionando las figus y luego 'Repes', o usando la Carga Masiva (CSV) en el menú lateral.")

@st.dialog("⚖️ Términos Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones")
    st.markdown(config.TEXTO_LEGAL_COMPLETO)
    st.divider()
    st.caption("Al usar esta aplicación, aceptás que Figus 26 es solo un intermediario de contacto.")


# ==========================================
#      FLUJO LÓGICO PRINCIPAL
# ==========================================

# 1. RECUPERAR ESTADO +18 DESDE LA URL
if "over18" in st.query_params:
    st.session_state.barrera_superada = True

# 2. LÓGICA DE AUTO-LOGIN (PERSISTENCIA DE SESIÓN)
if 'user' not in st.session_state or st.session_state.user is None:
    # Verificamos si hay un token en la URL
    query_params = st.query_params
    if "token" in query_params:
        uid = utils.validar_token_sesion(query_params["token"])
        if uid:
            # Recuperamos usuario silenciosamente
            restored_user = db.get_user_by_id(uid)
            if restored_user:
                st.session_state.user = restored_user
                # FIX: Si ya tiene sesión válida, asumimos que es +18
                st.session_state.barrera_superada = True

# 3. BARRERA DE EDAD (BLOQUEANTE)
if not st.session_state.barrera_superada:
    mostrar_barrera_entrada()
    st.stop() # Detiene la ejecución aquí

# 4. VERIFICACIÓN DE ESTADO DE USUARIO
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    # Si no hay usuario, mostramos Login
    auth.mostrar_login()
else:
    # --- USUARIO LOGUEADO ---
    user = st.session_state.user
    
    # ----------------------------------------------------
    #  LÓGICA DE ADMINISTRADOR (IMPLEMENTACIÓN N° 4)
    # ----------------------------------------------------
    if user.get('is_admin', False):
        # Si es admin, mostramos SU panel y detenemos el resto
        with st.sidebar:
            st.title("Admin Panel")
            if st.button("Salir / Logout"):
                st.session_state.user = None
                st.query_params.clear()
                st.rerun()
        
        # Renderizamos el panel admin importado
        admin.render_admin_panel(user)
        
    else:
        # ----------------------------------------------------
        #  FLUJO DE USUARIO NORMAL
        # ----------------------------------------------------
        
        # Inicializar desbloqueos en memoria
        if not st.session_state.unlocked_users:
            st.session_state.unlocked_users = db.get_unlocked_ids(user['id'])

        # Verificar Reset Diario
        if db.verify_daily_reset(user):
            if not user.get('is_premium', False):
                st.toast("📅 ¡Nuevo día! Se renovaron tus créditos.", icon="☀️")

        # Notificaciones Wishlist (Premium)
        if user.get('is_premium', False) and 'wishlist_notified' not in st.session_state:
            m_df = db.fetch_market(user['id'])
            matches, ventas = db.find_matches(user['id'], m_df)
            wish_hits = [x for x in matches + ventas if x.get('is_wishlist', False)]
            if wish_hits:
                qty = len(wish_hits)
                st.toast(f"🔔 ¡Atención! Hay {qty} figuritas de tu Wishlist disponibles.", icon="🎉")
            st.session_state.wishlist_notified = True

        # Preparación de datos del álbum
        seleccion_pais = st.session_state.get("seleccion_pais_key", list(config.ALBUM_PAGES.keys())[0])
        start, end = config.ALBUM_PAGES[seleccion_pais]
        
        # Calculo de total para barra de progreso
        total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
        # (Para visualización usamos el estado del país actual como aproximación)
        _, _, _, df_full = db.get_inventory_status(user['id'], start, end)
        try: tengo_total = df_full[df_full['status'] == 'tengo'].shape[0]
        except: tengo_total = 0
        
        # --- SIDEBAR ---
        with st.sidebar:
            st.title(f"Hola {user['nick']}")
            st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
            
            # EDITAR PERFIL
            if st.button("✏️ Editar Perfil", key="btn_edit_profile"):
                 mostrar_editar_perfil(user)
                 
            st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
            
            # TRANSACCIONES PENDIENTES
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
            st.progress(min(tengo_total / total_album, 1.0), text="🏆 Mi Álbum")
            
            # COMPARTIR DESEADOS
            full_wishlist = db.get_full_wishlist(user['id'])
            if full_wishlist:
                link_share = utils.generar_link_whatsapp_wishlist(full_wishlist)
                st.link_button("📢 Compartir Deseados", link_share, type="primary", use_container_width=True)
            
            st.divider()
            
            # CARGA MASIVA
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
            
            # ESTADO PREMIUM
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
            
            # LOGOUT
            if st.button("Chau / Salir"):
                st.session_state.user = None
                st.query_params.clear() # FIX: Borrar token al salir
                st.rerun()

        # --- PANTALLA PRINCIPAL ---
        st.header("📖 Mi Álbum")
        
        # --- NAVEGACIÓN SEGURA (POP-UP CAMBIOS) ---
        paises = list(config.ALBUM_PAGES.keys())
        try: idx = paises.index(st.session_state.current_country)
        except: idx = 0
        
        nuevo_pais = st.selectbox(
            "Sección:", 
            paises, 
            index=idx, 
            key="nav_pais_selector"
        )
        
        # Interceptamos el cambio si hay cosas sin guardar
        if nuevo_pais != st.session_state.current_country:
            if st.session_state.unsaved_changes:
                confirmar_cambio_pais(nuevo_pais, user)
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
        if fc1.button("📧 Contacto", width="stretch", type="secondary"): mostrar_contacto()
        if fc2.button("❓ FAQ", width="stretch", type="secondary"): mostrar_faq()
        if fc3.button("⚖️ Legales", width="stretch", type="secondary"): mostrar_legales()
        
        st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)