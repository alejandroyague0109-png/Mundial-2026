import streamlit as st
import pandas as pd
import time
import config
import database as db
import utils
import locations

# --- MODALES DE AYUDA Y NAVEGACIÓN ---

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
            st.toast("Perfil actualizado!", icon="✅"); time.sleep(1); st.rerun()
        else: st.error(msg)

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

# --- DIÁLOGOS FOOTER ---

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
    with st.expander("¿Es gratis usar la app?"): st.write("Sí, podés cargar tu álbum y ver el mercado gratis. Tenés 1 contacto diario gratuito.")
    with st.expander("¿Cómo funciona el Premium?"): st.write("Con Premium tenés contactos ilimitados, alertas de Wishlist y aparecés destacado en las búsquedas.")
    with st.expander("¿Qué pasa si un usuario no responde?"): st.write("Los tratos se cierran por WhatsApp. Si no responde, podés usar el botón 'Fichaje caído' en la pestaña de Pendientes.")
    with st.expander("¿Cómo cargo mis repetidas?"): st.write("Podés hacerlo manualmente en la sección 'Mi Álbum' marcando primero las que tenés y luego seleccionando las repetidas, o usando la Carga Masiva (CSV).")

@st.dialog("⚖️ Términos Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones"); st.markdown(config.TEXTO_LEGAL_COMPLETO); st.divider(); st.caption("Al usar esta aplicación, aceptás que Figus 26 es solo un intermediario de contacto.")

# --- RENDERIZADOR DEL FOOTER ---
def render_footer():
    st.divider()
    fc1, fc2, fc3 = st.columns(3)
    if fc1.button("📧 Contacto", width="stretch", type="secondary"): mostrar_contacto()
    if fc2.button("❓ FAQ", width="stretch", type="secondary"): mostrar_faq()
    if fc3.button("⚖️ Legales", width="stretch", type="secondary"): mostrar_legales()
    st.markdown("<div class='footer-text'>© 2026 Figus 26. Hecho en Mendoza 🍷</div>", unsafe_allow_html=True)