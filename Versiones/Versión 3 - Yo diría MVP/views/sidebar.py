import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 
import locations 
from views import market # Importamos market para el modal de premium

# --- MODALES ESPECÍFICOS DEL SIDEBAR ---

@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### Formato del Archivo
    Debe tener 3 columnas obligatorias:
    1. **num**: Número de la figurita.
    2. **status**: `tengo` o `repetida`.
    3. **price**: Precio (0 si es canje).
    """)

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

# --- FUNCIÓN PRINCIPAL DE RENDERIZADO ---
def render_user_sidebar(user):
    # Preparación de datos (Cálculos para la barra de progreso)
    # Nota: Usamos el país actual seleccionado para el cálculo visual rápido
    current_country = st.session_state.get('current_country', list(config.ALBUM_PAGES.keys())[0])
    start_curr, end_curr = config.ALBUM_PAGES[current_country]
    total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
    
    # Obtenemos inventario local para la barra (aprox)
    _, _, _, df_full = db.get_inventory_status(user['id'], start_curr, end_curr)
    try: tengo_total = df_full[df_full['status'] == 'tengo'].shape[0]
    except: tengo_total = 0

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
        # Barra de progreso (Visualización de la sección actual)
        st.progress(min(tengo_total / 200, 1.0), text=f"🏆 Progreso {current_country}")
        
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