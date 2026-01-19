import streamlit as st
import time
from urllib.parse import quote
import database as db
import locations
import utils
import config
import streamlit.components.v1 as components 
import triangulation # <--- Importamos el archivo nuevo

ITEMS_POR_PAGINA = 10

def reset_pagination():
    st.session_state.page_canjes = 1
    st.session_state.page_ventas = 1
    st.session_state.page_pendientes = 1

def change_page(key, delta):
    st.session_state[key] += delta

# --- MODALES ---
@st.dialog("📐 ¿Qué es la Triangulación?")
def modal_explicacion_triangulacion():
    st.markdown("""
    ### La jugada maestra 🧠
    A veces, **A** quiere lo que tiene **C**, pero **C** no quiere nada de **A**. 
    ¡El mercado se traba! Ahí entra **B** (el Puente) para destrabarlo.

    **La jugada a 3 toques:**
    1.  Vos le das una repe al **Puente**.
    2.  El **Puente** le da una suya al **Dueño** (la que el Dueño quería).
    3.  El **Dueño** te da a vos la figurita que buscás.

    **Requisito:**
    El sistema solo busca "Puentes" que vivan en tu misma **Provincia y Zona**.
    """)

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
            with utils.spinner_futbolero():
                db.consume_credit(user)
                db.log_unlock(user['id'], target_id)
                st.session_state.unlocked_users.add(target_id)
                time.sleep(1)
            st.rerun()
        else:
            st.error("Error: Te quedaste sin créditos por hoy.")

@st.dialog("💎 Pasate a Premium", width="small")
def mostrar_modal_premium():
    st.markdown(f"""
    ### 🚀 Límite Alcanzado
    **Tenés** 1 contacto gratis por día.
    **Jugá en Primera con Premium:**
    * 🔓 **Ilimitado:** Contactá sin restricciones.
    * 🔔 **Alertas Wishlist:** Aviso si aparece una difícil.
    * 📐 **Triangulaciones:** Acceso a cadenas de cambio.
    * 🌍 **Un pago único:** Todo el mundial.
    * ⭐ **Destacado:** Aparecés primero en las listas.
    ---
    ### Precio Final: **${config.PRECIO_PREMIUM}**
    """)
    st.link_button("👉 Pagá con Mercado Pago", config.MP_LINK, type="primary", use_container_width=True)

def render_card(item, tipo, user, is_pending_view=False):
    suffix = "pend" if is_pending_view else "mkt"
    
    is_target_premium = item.get('is_premium', False)
    
    with st.container(border=True):
        col_info, col_actions = st.columns([0.75, 0.25])
        target_id = item['target_id']
        fig_recibo = item['figu']
        
        is_wishlist = item.get('is_wishlist', False)
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

        # --- INFO ---
        with col_info:
            badges = []
            if is_target_premium:
                badges.append("<span style='background-color:#fff9c4; color:#f57f17; border:1px solid #fbc02d; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold; margin-right:5px;'>💎 PREMIUM</span>")
            if is_wishlist:
                badges.append("<span style='background-color:#ffebee; color:#c62828; padding:2px 6px; border-radius:4px; font-size:0.75em; font-weight:bold;'>❤️ TU DESEO</span>")
            
            if badges:
                st.markdown(" ".join(badges), unsafe_allow_html=True)

            nick_display = item['nick']
            if is_target_premium:
                nick_html = f"<span style='font-size: 1.25em; font-weight: bold; color: #e65100;'>{nick_display}</span>"
            else:
                nick_html = f"<span style='font-size: 1.25em; font-weight: bold;'>{nick_display}</span>"

            st.markdown(f"""
                <div style="line-height: 1.2; margin-top: 4px;">
                    {nick_html}
                    <span style="color: grey; font-size: 0.9em; margin-left: 8px;">📍 {item['zone']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            if tipo == 'canje':
                fig_entrego = item.get('te_pide', '?')
                st.markdown(f"""
                <div style="font-size: 1.15em; margin-top: 8px; margin-bottom: 5px;">
                    🔄 Cambia <b>#{fig_recibo}</b> por tu <b>#{fig_entrego}</b>
                </div>
                """, unsafe_allow_html=True)
            else:
                precio = item['price']
                st.markdown(f"""
                <div style="font-size: 1.15em; margin-top: 8px; margin-bottom: 5px;">
                    💰 Vende <b>#{fig_recibo}</b> a <b>${precio}</b>
                </div>
                """, unsafe_allow_html=True)
            
            st.caption(f"⭐ Reputación: {item.get('reputation', 0)}")

        # --- ACCIONES ---
        with col_actions:
            if is_unlocked:
                if phone_target: 
                    st.link_button("🟢 WhatsApp", link_wa, type="secondary", use_container_width=True)
                
                if is_pending_view:
                    if st.button("✅ Fichaje cerrado", key=f"pd_ok_{fig_recibo}_{target_id}_{suffix}", help="Concretar transacción", use_container_width=True):
                        es_premium = user.get('is_premium', False)
                        id_para_borrar = None if es_premium else target_id
                        
                        with utils.spinner_futbolero():
                            if tipo == 'canje':
                                ok, msg = db.register_exchange(user['id'], fig_entrego, fig_recibo, target_id_to_remove=id_para_borrar)
                            else:
                                ok, msg = db.register_purchase(user['id'], fig_recibo, target_id_to_remove=id_para_borrar)
                        
                        if ok: 
                            if not es_premium: st.session_state.unlocked_users.discard(target_id)
                            st.toast("¡Golazo!", icon="⚽"); st.success(msg); time.sleep(1.0); st.rerun()
                        else: st.error(msg)
                    
                    if st.button("❌ Fichaje caído", key=f"pd_no_{fig_recibo}_{target_id}_{suffix}", help="Cancelar transacción", use_container_width=True):
                         db.remove_unlock(user['id'], target_id)
                         st.session_state.unlocked_users.discard(target_id)
                         st.rerun()

            else:
                btn_lbl = "🔓 Desbloquear"
                if st.button(btn_lbl, key=f"ul_{tipo}_{fig_recibo}_{target_id}_{suffix}", type="secondary", use_container_width=True):
                    if db.check_contact_limit(user):
                        if st.session_state.skip_security_modal:
                            with utils.spinner_futbolero():
                                db.consume_credit(user)
                                db.log_unlock(user['id'], target_id)
                                st.session_state.unlocked_users.add(target_id)
                                time.sleep(0.5)
                            st.rerun()
                        else: modal_seguridad(target_id, user)
                    else: mostrar_modal_premium()
            
            if st.button("⭐ Votar", key=f"vt_{tipo}_{fig_recibo}_{target_id}_{suffix}", help="Recomendar usuario", use_container_width=True):
                ok, m = db.votar_usuario(user['id'], target_id)
                st.toast(m)

def paginar_y_mostrar(lista_items, tipo_key, tipo_card, user, is_pending_view=False):
    if not is_pending_view:
        unique_id = time.time()
        js = f"""
        <script>
            try {{
                var doc = window.parent.document;
                var target = doc.querySelector('[data-testid="stAppViewContainer"]');
                if (target) {{ target.scrollTop = 0; }} else {{ doc.body.scrollTop = 0; doc.documentElement.scrollTop = 0; }}
            }} catch(e) {{ console.log(e); }}
        </script>
        <div style="display:none;">{unique_id}</div>
        """
        components.html(js, height=0)
    
    if not lista_items:
        st.info("No hay resultados visibles.")
        return
    
    total_items = len(lista_items)
    total_pages = (total_items - 1) // ITEMS_POR_PAGINA + 1
    
    if tipo_key not in st.session_state: st.session_state[tipo_key] = 1
    if st.session_state[tipo_key] > total_pages: st.session_state[tipo_key] = 1
    
    curr_page = st.session_state[tipo_key]
    start_idx = (curr_page - 1) * ITEMS_POR_PAGINA
    end_idx = start_idx + ITEMS_POR_PAGINA
    batch = lista_items[start_idx:end_idx]
    
    for item in batch: 
        t_final = tipo_card
        if tipo_card == 'auto':
            t_final = 'venta' if item.get('price', 0) > 0 else 'canje'
        render_card(item, t_final, user, is_pending_view)
        
    st.divider()
    
    col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
    with col_p1:
        if curr_page > 1: st.button("⬅️", key=f"prev_{tipo_key}", on_click=change_page, args=(tipo_key, -1), use_container_width=True)
    with col_p2: st.markdown(f"<div style='text-align: center; padding-top: 5px;'>Pág {curr_page}/{total_pages}</div>", unsafe_allow_html=True)
    with col_p3:
        if curr_page < total_pages: st.button("➡️", key=f"next_{tipo_key}", on_click=change_page, args=(tipo_key, 1), use_container_width=True)

def render_market(user):
    st.subheader("🔍 Mercado")
    
    # Inicializar estado de triangulación
    if 'triang_results' not in st.session_state: st.session_state.triang_results = None

    with st.expander("🔎 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_prov = col_f1.multiselect("Provincia:", list(locations.ARGENTINA.keys()), on_change=reset_pagination)
        avail_zones = []
        if filtro_prov:
            for p in filtro_prov: avail_zones.extend(locations.ARGENTINA.get(p, []))
        filtro_zonas = col_f2.multiselect("Zona:", avail_zones, on_change=reset_pagination)
        filtro_num = col_f3.text_input("Figurita #:", on_change=reset_pagination)

    # --- SECCIÓN TRIANGULACIÓN (INTEGRADA) ---
    st.markdown("---")
    c_triang_1, c_triang_2 = st.columns([0.85, 0.15]) 
    
    if filtro_num:
        msg_info = f"¿No encontrás cambio directo por la **#{filtro_num}**?"
        lbl_btn = f"📐 Buscar Triangulación para #{filtro_num}"
    else:
        msg_info = "🚀 **Modo Experto:** ¿Buscás una figurita difícil? Probá la triangulación."
        lbl_btn = "📐 Buscar Triangulación"

    c_triang_1.info(msg_info)
    
    with c_triang_2:
        if st.button("ℹ️", key="btn_info_triang", help="Ayuda Triangulación"):
            modal_explicacion_triangulacion()

    if st.button(lbl_btn, type="primary", use_container_width=True):
        if not filtro_num:
            st.warning("⚠️ Primero escribí el número de la figurita que buscás en 'Figurita #'.")
        elif not user.get('is_premium', False):
            mostrar_modal_premium()
        else:
            with utils.spinner_futbolero():
                # Obtenemos las repetidas del usuario actual para saber qué puede ofrecer
                _, _, repes_info, _ = db.get_inventory_status(user['id'], 1, 999)
                mis_repes_ids = list(repes_info.keys())
                
                if not mis_repes_ids:
                    st.error("Necesitás cargar figuritas 'Repetidas' para triangular.")
                else:
                    try:
                        target_val = int(filtro_num)
                        # Llamamos al módulo nuevo
                        resultados = triangulation.buscar_triangulacion(user, target_val, mis_repes_ids)
                        st.session_state.triang_results = resultados
                        if not resultados:
                            st.warning("No se encontraron triangulaciones en tu zona para esta figurita.")
                    except ValueError:
                        st.error("Ingresá un número válido.")

    # MOSTRAR RESULTADOS TRIANGULACIÓN
    if st.session_state.triang_results:
        st.success(f"¡Se encontraron {len(st.session_state.triang_results)} caminos posibles!")
        
        for i, t in enumerate(st.session_state.triang_results):
            with st.container(border=True):
                st.markdown(f"### 📐 Triángulo Dorado")
                c1, c2, c3 = st.columns(3)
                c1.metric("1. Vos entregás", f"#{t['bridge_quiere']}", f"a {t['bridge_nick']}")
                c2.metric("2. Puente entrega", f"#{t['bridge_tiene']}", f"a {t['target_nick']}")
                c3.metric("3. Recibís", f"#{t['target_tiene']}", "de Objetivo")
                
                # Desencriptar teléfonos para el link
                bridge_phone = utils.decrypt_phone(t.get('bridge_phone_enc'))
                target_phone = utils.decrypt_phone(t.get('target_phone_enc'))
                
                if bridge_phone:
                    info_contacto_target = f"{t['target_nick']} (WhatsApp: +549{target_phone})" if target_phone else t['target_nick']
                    msg_wa = f"Hola! Vi una triangulación en Figus26. Yo te doy la #{t['bridge_quiere']}, vos le das la #{t['bridge_tiene']} a *{info_contacto_target}*, y yo recibo la #{t['target_tiene']}. ¿Te copás?"
                    msg_encoded = quote(msg_wa)
                    link = f"https://wa.me/549{bridge_phone}?text={msg_encoded}"
                    
                    # Botón que abre WA y resetea (usando JS)
                    if st.button(f"Contactar al Puente ({t['bridge_nick']})", key=f"btn_triang_{i}", type="primary", use_container_width=True):
                         js = f"<script>window.open('{link}', '_blank').focus();</script>"
                         components.html(js, height=0)
                         st.toast("Abriendo WhatsApp...", icon="🚀")
                         time.sleep(1.5)
                         st.session_state.triang_results = None
                         st.rerun()
                else:
                    st.error("Error al obtener contacto del puente.")
        st.divider()

    # --- FLUJO NORMAL DE MERCADO ---
    with utils.spinner_futbolero():
        market_df = db.fetch_market(user['id'])
    
    matches, ventas = db.find_matches(user['id'], market_df)

    try:
        prem_response = db.supabase.table("users").select("id").eq("is_premium", True).execute()
        premium_ids = {u['id'] for u in prem_response.data}
    except:
        premium_ids = set()

    for m in matches: m['is_premium'] = m['target_id'] in premium_ids
    for v in ventas: v['is_premium'] = v['target_id'] in premium_ids

    def get_sort_score(item):
        is_p = item.get('is_premium', False)
        is_w = item.get('is_wishlist', False)
        if is_p and is_w: return 0
        if is_p and not is_w: return 1
        if not is_p and is_w: return 2
        return 3

    matches = sorted(matches, key=lambda x: (get_sort_score(x), x['figu']))
    ventas = sorted(ventas, key=lambda x: (get_sort_score(x), x['figu']))

    unlocked_ids = st.session_state.unlocked_users
    pendientes_total = []
    if unlocked_ids:
        p_df = market_df[market_df['user_id'].isin(unlocked_ids)]
        p_match, p_ventas = db.find_matches(user['id'], p_df)
        pendientes_total = p_match + p_ventas

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
    pendientes_filtrados = aplicar(pendientes_total)

    total_raw_c = len(matches)
    total_raw_v = len(ventas)
    
    if (total_raw_c > len(matches_filtrados)) or (total_raw_v > len(ventas_filtradas)):
        st.caption(f"📊 **Resumen:** Se encontraron **{total_raw_c} canjes** y **{total_raw_v} ventas** en total.")

    t1, t2, t3 = st.tabs(["🔄 Canjes", "💰 Ventas", "🤝 Pendientes"])
    
    with t1: 
        st.caption(f"Resultados: {len(matches_filtrados)}")
        paginar_y_mostrar(matches_filtrados, 'page_canjes', 'canje', user, is_pending_view=False)
    with t2: 
        st.caption(f"Resultados: {len(ventas_filtradas)}")
        paginar_y_mostrar(ventas_filtradas, 'page_ventas', 'venta', user, is_pending_view=False)
    with t3: 
        st.caption(f"Activos: {len(pendientes_filtrados)}")
        if not pendientes_filtrados:
            st.info("No hay negociaciones pendientes.")
        else:
            paginar_y_mostrar(pendientes_filtrados, 'page_pendientes', 'auto', user, is_pending_view=True)