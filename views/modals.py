import streamlit as st
import pandas as pd
import config
import database as db
import utils

# --- 1. BARRERA DE EDAD ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes.")
    st.markdown("**Al continuar, declarás bajo juramento que sos mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", width="stretch"):
        st.session_state.barrera_superada = True
        st.query_params["over18"] = "true"
        st.rerun()

# --- 2. NAVEGACIÓN SEGURA (LÓGICA CRÍTICA DE GUARDADO) ---
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

@st.dialog("❓ FAQ")
def mostrar_faq():
    with st.expander("¿Es gratis?"): st.write("Sí, con límite diario.")
    with st.expander("¿Premium?"): st.write("Ilimitado y alertas.")

@st.dialog("⚖️ Legales")
def mostrar_legales():
    st.markdown("### Términos y Condiciones"); st.markdown(config.TEXTO_LEGAL_COMPLETO)