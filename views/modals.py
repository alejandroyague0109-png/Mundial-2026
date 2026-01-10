import streamlit as st
import pandas as pd
import config
import database as db
import utils

# --- 1. BARRERA DE EDAD ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    st.markdown("**Al continuar, declarás bajo juramento que sos mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", width="stretch"):
        st.session_state.barrera_superada = True
        st.query_params["over18"] = "true"
        st.rerun()

# --- 2. NAVEGACIÓN SEGURA ---
@st.dialog("⚠️ Cambios sin guardar")
def confirmar_cambio_pais(target_pais, user):
    st.write(f"Tenés cambios pendientes en **{st.session_state.current_country}**.")
    st.warning("¿Querés guardar antes de salir?")
    
    col1, col2 = st.columns(2)
    
    # Opción 1: Guardar y Continuar
    if col1.button("💾 Guardar y Continuar", type="primary", width="stretch"):
        curr = st.session_state.current_country
        tengo_data = st.session_state.get(f"pills_tengo_{curr}", [])
        wish_data = st.session_state.get(f"pills_wish_{curr}", [])
        
        # --- LÓGICA DE RECUPERACIÓN (SNAPSHOT + DELTAS) ---
        snapshot_key = f"snapshot_df_{curr}"
        editor_key = f"editor_{curr}"
        
        # A. Recuperar Base
        if snapshot_key in st.session_state:
            df_repes = st.session_state[snapshot_key].copy()
        else:
            # Fallback
            repes_ids = st.session_state.get(f"repes_{curr}", [])
            df_repes = pd.DataFrame([{"Figurita": r, "Modo": "Canje", "Precio": 0, "Cantidad": 1} for r in repes_ids])

        # B. Aplicar Cambios Pendientes del Editor
        if editor_key in st.session_state:
            cambios = st.session_state[editor_key]
            if "edited_rows" in cambios:
                for idx_str, updated_cols in cambios["edited_rows"].items():
                    idx = int(idx_str)
                    if idx in df_repes.index:
                        for col, val in updated_cols.items():
                            df_repes.at[idx, col] = val
        # --------------------------------------------------

        with utils.spinner_futbolero():
             s, e = config.ALBUM_PAGES[curr]
             db.save_inventory_positive(user['id'], s, e, tengo_data, wish_data, df_repes)
        
        st.session_state.unsaved_changes = False
        st.session_state.current_country = target_pais
        st.rerun()
        
    # Opción 2: Descartar
    if col2.button("🗑️ Descartar Cambios", width="stretch"):
        st.session_state.unsaved_changes = False
        st.session_state.current_country = target_pais
        st.rerun()

# --- 3. MODALES INFORMATIVOS (FOOTER) ---
@st.dialog("📧 Contacto")
def mostrar_contacto():
    st.markdown("### Soporte\n* 📧 soporte@figus26.com\n* 📷 @figus26_oficial")

@st.dialog("❓ Preguntas Frecuentes")
def mostrar_faq():
    st.markdown("### ⚽ Guía rápida")
    
    with st.expander("🤔 ¿Cómo funciona?"):
        st.markdown("""
        1. **Mi Álbum:** Entrá a la sección de tu país/equipo.
        2. **Cargá:** Marcá las que **TENÉS** y las que **DESEÁS** (Wishlist).
        3. **Repes:** Si tenés repetidas, marcalas abajo para canje o venta.
        4. **Mercado:** El sistema cruza datos y te muestra quién tiene lo que buscás y quiere lo que vos tenés (Match).
        """)

    with st.expander("💸 ¿Es gratis?"):
        st.markdown("""
        **Sí.** Podés usar la app totalmente gratis. 
        Tenés **1 crédito diario** para contactar (ver el WhatsApp) de otro coleccionista.
        Los créditos se renuevan cada 24hs automáticamente.
        """)

    with st.expander("💎 ¿Qué beneficios tiene ser Premium?"):
        st.markdown("""
        Por un único pago (acceso todo el mundial), obtenés:
        * 🔓 **Contactos Ilimitados:** Sin restricciones diarias.
        * 📐 **Triangulación:** Acceso a la herramienta de canjes a 3 bandas.
        * 🥇 **Prioridad:** Tus cartas aparecen primeras y con borde dorado.
        * 🔔 **Alertas:** Te avisamos si alguien carga una figu de tu Wishlist.
        """)

    with st.expander("📐 ¿Qué es la Triangulación?"):
        st.markdown("""
        Es una función avanzada para **Usuarios Premium**.
        Si nadie quiere hacer un cambio directo con vos (A <-> B), el sistema busca un **Puente** (C) en tu misma zona para hacer un canje circular:
        **Vos -> Puente -> Objetivo -> Vos**.
        """)

    with st.expander("🛡️ Seguridad"):
        st.markdown("""
        * Reunite siempre en **lugares públicos** y concurridos.
        * Revisá bien las figuritas antes de cerrar el trato.
        * **Nunca envíes dinero** por adelantado.
        * Figus 26 conecta partes pero no participa de la transacción.
        """)

@st.dialog("⚖️ Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones"); st.markdown(config.TEXTO_LEGAL_COMPLETO)