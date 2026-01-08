import streamlit as st
import database as db
import utils
import time
import config

# --- MODAL PREMIUM (COMPLETO) ---
@st.dialog("💎 Hacete Premium")
def mostrar_modal_premium():
    st.markdown("### 🚀 ¡Llevá tu colección a otro nivel!")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Gratis")
        st.write("❌ Límite: 1 contacto x día")
        st.write("❌ Sin alertas")
        st.write("❌ Visibilidad normal")
    
    with c2:
        st.markdown("#### 💎 Premium")
        st.write("✅ **Contactos Ilimitados**")
        st.write("✅ **Alertas de Wishlist**")
        st.write("✅ **Destacado en búsquedas**")
    
    st.divider()
    st.markdown(f"<h3 style='text-align: center'>Precio: ${config.PRECIO_PREMIUM} / mes</h3>", unsafe_allow_html=True)
    st.info("Para activar, enviá el pago al alias y luego cargá el ID de operación en el menú lateral.")
    
    st.markdown("#### 💸 Datos de Pago")
    st.code("figus26.mp", language="text")
    st.caption("Titular: Figus 26 App")

# --- RENDERIZADO DEL MERCADO ---
def render_market(user):
    st.header("🌍 Mercado de Figus")
    
    # --- FILTROS ---
    c_filt1, c_filt2 = st.columns([2, 1])
    filtro_zona = c_filt1.toggle("📍 Ver solo gente de mi zona", value=True)
    
    # --- OBTENCIÓN DE DATOS ---
    with utils.spinner_futbolero():
        # Traemos todo el mercado excepto lo mío
        market_df = db.fetch_market(user['id'])
    
    # Buscamos coincidencias
    matches, ventas = db.find_matches(user['id'], market_df)
    
    # Aplicamos filtro de zona si está activo
    if filtro_zona:
        m_zone = user.get('zone', '')
        matches = [m for m in matches if m['zone'] == m_zone]
        ventas = [v for v in ventas if v['zone'] == m_zone]
    
    # --- TABS DE VISUALIZACIÓN ---
    tab_canjes, tab_ventas = st.tabs([f"🔄 Canjes ({len(matches)})", f"💲 Ventas ({len(ventas)})"])
    
    # Función interna para dibujar cada tarjeta (Card)
    def mostrar_tarjeta(item, tipo):
        """Renderiza una tarjeta de usuario con lógica de desbloqueo."""
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            
            # Columna Izquierda: Datos del Usuario y la Figurita
            with c1:
                st.markdown(f"**{item['nick']}** ({item['province']})")
                st.caption(f"📍 {item['zone']} | ⭐ Rep: {item['reputation']}")
                
                if tipo == 'canje':
                    st.success(f"✅ Tiene la **#{item['figu']}**")
                    # 'te_pide' es la que vos tenés repetida y él necesita
                    st.info(f"🔄 Busca la **#{item.get('te_pide', '?')}** (que vos tenés)")
                else:
                    st.success(f"🛒 Vende la **#{item['figu']}**")
                    st.markdown(f"💰 **Precio: ${item['price']}**")
            
            # Columna Derecha: Botón de Acción
            with c2:
                target_id = item['target_id']
                # Verificamos si ya pagué/gasté crédito para ver a este usuario
                is_unlocked = target_id in st.session_state.unlocked_users
                
                if is_unlocked:
                    # SI ESTÁ DESBLOQUEADO: Botón de WhatsApp
                    # Usamos decrypt_phone robusto para evitar errores
                    real_phone = utils.decrypt_phone(item['phone_encrypted'])
                    
                    msg_wa = f"Hola {item['nick']}! Vi en Figus26 que tenés la {item['figu']}. "
                    if tipo == 'canje': msg_wa += f"Te la cambio por la {item.get('te_pide', '?')}."
                    else: msg_wa += "Te la quiero comprar."
                    
                    url_wa = f"https://wa.me/{real_phone}?text={utils.quote(msg_wa)}"
                    st.link_button("💬 WhatsApp", url_wa, type="primary", use_container_width=True)
                
                else:
                    # SI ESTÁ BLOQUEADO: Botón para gastar crédito
                    if st.button("🔓 Contactar", key=f"btn_{tipo}_{item['figu']}_{target_id}", use_container_width=True):
                        # 1. Chequeamos si tiene saldo (o es premium)
                        if db.check_contact_limit(user):
                            # 2. Intentamos registrar el desbloqueo en DB
                            if db.log_unlock(user['id'], target_id):
                                # 3. Consumimos el crédito (si es gratis)
                                db.consume_credit(user)
                                # 4. Actualizamos memoria local
                                st.session_state.unlocked_users.add(target_id)
                                
                                # 5. Registramos la "Intención" para las estadísticas
                                if tipo == 'canje':
                                    db.register_exchange(user['id'], item.get('te_pide'), item['figu'], target_id)
                                else:
                                    db.register_purchase(user['id'], item['figu'], target_id)
                                
                                st.toast("¡Contacto desbloqueado!", icon="🔓")
                                time.sleep(1)
                                st.rerun() # Recargamos para mostrar el botón de WhatsApp
                            else:
                                st.error("Error de conexión.")
                        else:
                            # Si no tiene saldo
                            st.error("Límite diario alcanzado.")
                            time.sleep(1.5)
                            mostrar_modal_premium()

    # --- RENDERIZADO TAB CANJES ---
    with tab_canjes:
        if not matches:
            st.info("No hay canjes directos (Match) en tu zona por ahora.")
            st.caption("Tip: Cargá más repetidas para aumentar tus chances.")
        else:
            # Paginación
            pag_size = 5
            total_items = len(matches)
            total_p = (total_items - 1) // pag_size + 1
            
            # Control de página segura
            if st.session_state.page_canjes > total_p: st.session_state.page_canjes = 1
            page = st.session_state.page_canjes
            
            start_idx = (page - 1) * pag_size
            end_idx = start_idx + pag_size
            
            # Loop de tarjetas
            for m in matches[start_idx:end_idx]:
                mostrar_tarjeta(m, 'canje')
            
            # Controles de Paginación
            if total_p > 1:
                col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                if col_p1.button("⬅️ Ant", key="p_c_prev") and page > 1:
                    st.session_state.page_canjes -= 1
                    st.rerun()
                col_p2.markdown(f"<p style='text-align:center'>Página {page} de {total_p}</p>", unsafe_allow_html=True)
                if col_p3.button("Sig ➡️", key="p_c_next") and page < total_p:
                    st.session_state.page_canjes += 1
                    st.rerun()

    # --- RENDERIZADO TAB VENTAS ---
    with tab_ventas:
        if not ventas:
            st.info("No hay figuritas a la venta que te sirvan.")
        else:
            # Paginación
            pag_size = 5
            total_items = len(ventas)
            total_p = (total_items - 1) // pag_size + 1
            
            if st.session_state.page_ventas > total_p: st.session_state.page_ventas = 1
            page = st.session_state.page_ventas
            
            start_idx = (page - 1) * pag_size
            end_idx = start_idx + pag_size
            
            for v in ventas[start_idx:end_idx]:
                mostrar_tarjeta(v, 'venta')
            
            if total_p > 1:
                col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
                if col_p1.button("⬅️ Ant", key="p_v_prev") and page > 1:
                    st.session_state.page_ventas -= 1
                    st.rerun()
                col_p2.markdown(f"<p style='text-align:center'>Página {page} de {total_p}</p>", unsafe_allow_html=True)
                if col_p3.button("Sig ➡️", key="p_v_next") and page < total_p:
                    st.session_state.page_ventas += 1
                    st.rerun()