import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils
from views import market, layout # Importamos layout para usar los modales (CSV help, Edit profile)

def render_sidebar(user):
    with st.sidebar:
        st.title(f"Hola {user['nick']}")
        st.caption(f"📍 {user.get('province', '')} - {user.get('zone', '')}")
        
        # Botón Editar Perfil
        if st.button("✏️ Editar Perfil", key="btn_edit_profile"):
             layout.mostrar_editar_perfil(user)
             
        st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
        
        # Notificaciones de Transacciones Pendientes
        pending_requests = db.get_pending_transactions(user['id'])
        if pending_requests:
            st.divider()
            st.warning(f"🔔 Tenés {len(pending_requests)} confirmaciones")
            for req in pending_requests:
                with st.expander(f"De {req['users']['nick']}", expanded=True):
                    if req['type'] == 'exchange': st.caption(f"Te dio la **#{req['fig_sent']}**, vos **#{req['fig_received']}**")
                    else: st.caption(f"Te compró la **#{req['fig_received']}**")
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
        # Usamos el pais actual para saber dónde estamos, pero calculamos total
        current_country = st.session_state.get('current_country', list(config.ALBUM_PAGES.keys())[0])
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
            if col_a.button("❓ Ayuda", width="stretch"): layout.mostrar_instrucciones_csv()
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