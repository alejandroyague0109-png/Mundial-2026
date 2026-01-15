import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils 
import locations 
from views import market 

# --- MODALES ESPECÍFICOS DEL SIDEBAR ---

@st.dialog("📲 Instalar App")
def mostrar_instrucciones_instalacion():
    st.markdown("### ¿Cómo tener Figus 26 en tu inicio?")
    st.markdown("Al instalarla, funcionará como una app nativa: pantalla completa y acceso rápido.")
    
    tab_android, tab_ios = st.tabs(["🤖 Android", "🍎 iPhone (iOS)"])
    
    with tab_android:
        st.info("Para **Chrome** en Android:")
        st.markdown("""
        1. Tocá los **3 puntitos (⋮)** arriba a la derecha.
        2. Buscá la opción **'Instalar aplicación'** o **'Agregar a la pantalla principal'**.
        3. Confirmá y ¡listo!
        """)
        # Ejemplo visual simulado con texto
        st.caption("Tip: Si no ves la opción, actualizá Chrome.")

    with tab_ios:
        st.info("Para **Safari** en iPhone:")
        st.markdown("""
        1. Tocá el botón **Compartir** (cuadrado con flecha hacia arriba).
        2. Bajá hasta encontrar **'Agregar al Inicio'** (Add to Home Screen).
        3. Dale a **'Agregar'**.
        """)

@st.dialog("⚡ Guía de Carga Rápida")
def mostrar_ayuda_carga_rapida():
    st.markdown("""
    ### 🚀 Cómo cargar tus figus volando
    Olvidate de buscar número por número. Hacelo por país.

    **1. Elegí el Equipo:** (Ej: Argentina).
    **2. Escribí los números:** Usá comas, espacios, enters o guiones para rangos.
    * Ejemplo: `1, 2, 5-10, 15` (Carga la 1, 2, 5, 6, 7, 8, 9, 10 y 15).

    ### 🧠 Inteligencia Artificial
    * **🟦 Tengo:** Las que pegaste en el álbum.
    * **🟩 Repetidas:** Las que tenés para cambiar. **Si ponés una acá, el sistema asume que la TENÉS.** No hace falta ponerla en la caja azul.
    * **🟥 Wishlist:** Las que te faltan. Si el sistema detecta que ya la tenés (o es repe), la ignora para evitar errores.
    
    ⚠️ **Nota:** Al procesar, se borrará lo que hayas cargado antes **solo para ese país** y se reemplazará por lo nuevo.
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

    if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
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
    with st.sidebar:
        st.title(f"Hola {user['nick']}")
        st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
        
        # EDITAR PERFIL
        if st.button("✏️ Editar Perfil", key="btn_edit_profile"):
             mostrar_editar_perfil(user)
        
        # --- NUEVO BOTÓN: INSTALAR APP ---
        # Lo ponemos visible y destacado arriba
        if st.button("📲 Instalar App", type="secondary", use_container_width=True, help="Agregá Figus 26 a tu inicio"):
            mostrar_instrucciones_instalacion()
             
        st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
        
        # --- TRANSACCIONES PENDIENTES ---
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
        
        # --- BARRA DE PROGRESO GLOBAL ---
        total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])
        pegadas_reales = db.get_completion_stats(user['id'])
        
        progreso = 0.0
        if total_album > 0:
            progreso = min(pegadas_reales / total_album, 1.0)
            
        st.progress(progreso, text=f"🏆 Progreso Total: {pegadas_reales}/{total_album}")
        
        # --- COMPARTIR DESEADOS ---
        full_wishlist = db.get_full_wishlist(user['id'])
        if full_wishlist:
            link_share = utils.generar_link_whatsapp_wishlist(full_wishlist)
            st.link_button("📢 Compartir Deseados", link_share, type="primary", use_container_width=True)
        
        st.divider()
        
        # --- CARGA RÁPIDA INTELIGENTE ---
        with st.expander("⚡ Carga Rápida (Por Página)", expanded=False):
            st.caption("Elegí el país y cargá los números de esa página (ej: 1 al 19).")
            
            opciones_paginas = list(config.ALBUM_PAGES.keys())
            page_key = st.selectbox("Seleccioná Equipo:", opciones_paginas)
            
            start_id, end_id = config.ALBUM_PAGES[page_key]
            
            if st.button("❓ ¿Cómo funciona?", key="btn_help_smart", use_container_width=True):
                mostrar_ayuda_carga_rapida()
            
            st.markdown("**🟦 TENGO (Pegadas)**")
            txt_tengo = st.text_area("Lista Tengo", placeholder="Ej: 1-5, 8, 11", height=70, label_visibility="collapsed")
            
            st.markdown("**🟩 REPETIDAS (Para cambiar)**")
            txt_repes = st.text_area("Lista Repes", placeholder="Ej: 5, 9 (Se agregan a 'Tengo' solas)", height=70, label_visibility="collapsed")
            
            st.markdown("**🟥 WISHLIST (Buscadas)**")
            txt_wish = st.text_area("Lista Deseados", placeholder="Ej: 15-19", height=70, label_visibility="collapsed")
            
            short_name = page_key.split('-')[0].strip()
            
            if st.button(f"🚀 Procesar {short_name}", type="primary", use_container_width=True):
                with utils.spinner_futbolero():
                    ids_tengo = utils.parse_smart_input(txt_tengo, start_id, end_id)
                    ids_repes = utils.parse_smart_input(txt_repes, start_id, end_id)
                    ids_wish = utils.parse_smart_input(txt_wish, start_id, end_id)
                    
                    ok, msg = db.bulk_smart_update(user['id'], start_id, end_id, ids_tengo, ids_repes, ids_wish)
                
                if ok:
                    st.toast(f"¡{short_name} Actualizado!", icon="✅")
                    st.success(msg)
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(msg)
        
        st.divider()
        
        # --- ESTADO PREMIUM ---
        if user.get('is_premium', False): 
            st.success("💎 PREMIUM")
        else:
            st.info("👤 GRATIS")
            contacts = user.get('daily_contacts_count', 0)
            if contacts >= 1: st.progress(1.0, text="Límite: 1/1 (Agotado)")
            else: st.progress(0.0, text="Límite: 0/1 (Disponible)")
            
            if st.button("💎 Hacete Premium", use_container_width=True): 
                market.mostrar_modal_premium()
            
            with st.expander("Validar Pago"):
                op = st.text_input("ID Op")
                if op and st.button("Validar", use_container_width=True):
                    with utils.spinner_futbolero():
                        ok, msg = db.verificar_pago_mp(op, user['id'])
                    if ok: st.toast("¡Premium!", icon="💎"); st.rerun()
                    else: st.error(msg)
        
        # --- LOGOUT ---
        if st.button("Chau / Salir", use_container_width=True):
            st.session_state.user = None
            st.query_params.clear() 
            st.rerun()