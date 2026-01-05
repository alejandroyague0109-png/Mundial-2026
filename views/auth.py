import streamlit as st
import time
import database as db
import locations
import config

def mostrar_login():
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    
    with t1:
        p = st.text_input("Teléfono", key="l_p", placeholder="Ej: 2604...")
        pw = st.text_input("Contraseña", type="password", key="l_pw")
        
        if st.button("Entrar", type="primary", use_container_width=True):
            u, m = db.login_user(p, pw)
            if u: st.session_state.user = u; st.rerun()
            else: st.error(m)
            
    with t2:
        n = st.text_input("Nick / Apodo")
        ph = st.text_input("Teléfono", key="r_p", placeholder="Ej: 2604...")
        pw2 = st.text_input("Contraseña", type="password", key="r_pw")
        
        col_prov, col_dep = st.columns(2)
        reg_prov = col_prov.selectbox("Provincia", list(locations.ARGENTINA.keys()), index=None, placeholder="Seleccioná Provincia...")
        opciones_deptos = locations.ARGENTINA.get(reg_prov, []) if reg_prov else []
        reg_zone = col_dep.selectbox("Departamento / Barrio", opciones_deptos, index=None, placeholder="Seleccioná Zona...")
        
        st.divider()
        col_legales, col_check = st.columns([1, 2])
        
        # Callback para ver contrato
        def ver_contrato():
             @st.dialog("📄 Términos", width="large")
             def _dialog(): st.markdown(config.TEXTO_LEGAL_COMPLETO)
             _dialog()

        col_legales.button("📄 Leer Legales", type="secondary", on_click=ver_contrato, use_container_width=True)
        acepto = col_check.checkbox("Acepto términos y condiciones")
        
        campos_completos = n and ph and pw2 and reg_prov and reg_zone and acepto
        
        if st.button("Registrarme", type="primary", disabled=(not campos_completos), use_container_width=True):
            u, m = db.register_user(n, ph, reg_prov, reg_zone, pw2)
            if u: 
                st.toast("¡Alta incorporación! Bienvenido al equipo.", icon="⚽")
                st.success("Te creaste la cuenta. Ahora entrá.")
                time.sleep(2)
            else: st.error(m)