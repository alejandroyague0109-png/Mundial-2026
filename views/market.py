import streamlit as st
import time
from urllib.parse import quote
import database as db
import locations
import utils
import config

ITEMS_POR_PAGINA = 15

def reset_pagination():
    st.session_state.page_canjes = 1
    st.session_state.page_ventas = 1

def change_page(key, delta):
    st.session_state[key] += delta

# --- MODAL SEGURIDAD ---
@st.dialog("🛡️ Consejos de Seguridad")
def modal_seguridad(target_id, user):
    st.markdown("### ⚠️ Antes de contactar:")
    st.info("Para jugar tranquilo en este mercado:")
    st.markdown("""
    * 🏢 **Campo Neutral:** Juntate siempre en zonas públicas y concurridas.
    * 👀 **VAR:** Revisá el estado de las figus antes de entregar las tuyas.
    * 💰 **Sin Adelantos:** No mandes plata antes del encuentro.
    """)
    st.divider()
    st.caption("Si confirmás, usás 1 crédito diario (si no sos Premium) para ver el número.")
    
    no_volver_a_mostrar = st.checkbox("No me mostrés esto de nuevo", key="chk_skip_sec")
    
    if st.button("✅ Dale, Ver Contacto", type="primary", use_container_width=True):
        if no_volver_a_mostrar: st.session_state.skip_security_modal = True
        
        if db.check_contact_limit(user):
            db.consume_credit(user)
            st.session_state.unlocked_users.add(target_id)
            st.rerun()
        else:
            st.error("Error: Te quedaste sin créditos por hoy.")

# --- MODAL PREMIUM ---
@st.dialog("💎 Pasate a Premium", width="small")
def mostrar_modal_premium():
    st.markdown(f"""
    ### 🚀 Límite Alcanzado
    **Tenés** 1 contacto gratis por día.
    **Jugá en Primera con Premium:**
    * 🔓 **Ilimitado:** Contactá sin restricciones.
    * 📐 **Triangulaciones:** Acceso a cadenas de cambio.
    * 🌍 **Un pago único:** Todo el mundial.
    * ⭐ **Destacado:** Aparecés primero en las listas.
    ---
    ### Precio Final: **${config.PRECIO_PREMIUM}**
    """)
    st.link_button("👉 Pagá con Mercado Pago", config.MP_LINK, type="primary", use_container_width=True)

def render_card(item, tipo, user):
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        target_id = item['target_id']
        fig_recibo = item['figu']
        is_unlocked = target_id in st.session_state.unlocked_users
        phone_target = None
        link_wa = "#"
        
        if is_unlocked:
            phone_target = utils.decrypt_phone(item.get('phone_encrypted'))
            if phone_target:
                if tipo == 'canje':
                    fig_entrego = item.get('te_pide', '?')
                    texto_base = f"Hola! Vi en Figus 26 que cambiás la #{fig_recibo} por la #{fig_entrego}. ¿Hacemo cambio?"
                else:
                    precio = item['price']
                    texto_base = f"Hola! Vi en Figus 26 que vendés la #{fig_recibo} a ${precio}. ¿La tenés?"
                mensaje_encoded = quote(texto_base)
                link_wa = f"https://wa.me/549{phone_target}?text={mensaje_encoded}"
            else: st.error("Error al desencriptar.")

        loc_str = f"{item['province']} - {item['zone']}"
        if tipo == 'canje':
            fig_entrego = item.get('te_pide', '?')
            c1.markdown(f"🔄 **{item['nick']}**")
            c1.caption(f"📍 {loc_str}")
            c1.markdown(f"Cambia **#{fig_recibo}** por tu **#{fig_entrego}**")
        else:
            precio = item['price']
            c1.markdown(f"💰 **{item['nick']}**")
            c1.caption(f"📍 {loc_str}")
            c1.markdown(f"Vende **#{fig_recibo}** a **${precio}**")

        if is_unlocked:
            if phone_target: c2.link_button("🟢 Abrir Chat", link_wa, use_container_width=True)
            if tipo == 'canje':
                with c1.expander("⚙️ Confirmar"):
                    if st.button(f"✅ Registrar #{fig_recibo}", key=f"swap_{fig_recibo}_{target_id}"):
                        ok, msg = db.register_exchange(user['id'], fig_entrego, fig_recibo)
                        if ok: st.toast("¡Golazo!", icon="⚽"); st.success(msg); time.sleep(3); st.rerun()
                        else: st.error(msg)
        else:
            if c2.button("🔓 Contactar", key=f"ul_{tipo}_{fig_recibo}_{target_id}", use_container_width=True):
                if db.check_contact_limit(user):
                    if st.session_state.skip_security_modal:
                        db.consume_credit(user)
                        st.session_state.unlocked_users.add(target_id)
                        st.rerun()
                    else: modal_seguridad(target_id, user)
                else: mostrar_modal_premium()
        
        if c3.button("👍", key=f"vt_{tipo}_{fig_recibo}_{target_id}"):
            ok, m = db.votar_usuario(user['id'], target_id)
            st.toast(m)

def paginar_y_mostrar(lista_items, tipo_key, tipo_card, user):
    if not lista_items:
        st.info("No encontramos nada con estos filtros.")
        return
    total_items = len(lista_items)
    total_pages = (total_items - 1) // ITEMS_POR_PAGINA + 1
    if st.session_state[tipo_key] > total_pages: st.session_state[tipo_key] = 1
    curr_page = st.session_state[tipo_key]
    start_idx = (curr_page - 1) * ITEMS_POR_PAGINA
    end_idx = start_idx + ITEMS_POR_PAGINA
    batch = lista_items[start_idx:end_idx]
    
    for item in batch: render_card(item, tipo_card, user)
    st.divider()
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p1:
        if curr_page > 1: st.button("⬅️ Anterior", key=f"prev_{tipo_key}", on_click=change_page, args=(tipo_key, -1), use_container_width=True)
    with col_p2: st.markdown(f"<div style='text-align: center; padding-top: 5px;'><b>Página {curr_page} de {total_pages}</b></div>", unsafe_allow_html=True)
    with col_p3:
        if curr_page < total_pages: st.button("Siguiente ➡️", key=f"next_{tipo_key}", on_click=change_page, args=(tipo_key, 1), use_container_width=True)

def render_market(user):
    st.subheader("🔍 Mercado")
    with st.expander("🔎 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_prov = col_f1.multiselect("Provincia:", list(locations.ARGENTINA.keys()), default=[user.get('province', 'Mendoza')], on_change=reset_pagination)
        avail_zones = []
        if filtro_prov:
            for p in filtro_prov: avail_zones.extend(locations.ARGENTINA.get(p, []))
        filtro_zonas = col_f2.multiselect("Depto / Barrio:", avail_zones, on_change=reset_pagination)
        filtro_num = col_f3.text_input("Buscá por número:", placeholder="Ej: 10", on_change=reset_pagination)

    market_df = db.fetch_market(user['id'])
    matches, ventas = db.find_matches(user['id'], market_df)

    # Aplicar filtros
    def aplicar(lista):
        res = []
        for i in lista:
            if filtro_prov and i['province'] not in filtro_prov: continue
            if filtro_zonas and i['zone'] not in filtro_zonas: continue
            if filtro_num and str(i['figu']) != filtro_num: continue
            res.append(i)
        return res

    matches_filtrados = aplicar(matches)
    ventas_filtradas = aplicar(ventas)

    t1, t2 = st.tabs([f"Canjes ({len(matches_filtrados)})", f"Ventas ({len(ventas_filtradas)})"])
    with t1: paginar_y_mostrar(matches_filtrados, 'page_canjes', 'canje', user)
    with t2: paginar_y_mostrar(ventas_filtradas, 'page_ventas', 'venta', user)