import streamlit as st
import time
import database as db
import locations
import utils
import config

# --- DIALOGO PARA TÉRMINOS Y CONDICIONES (POP-UP) ---
@st.dialog("📜 Términos y Condiciones")
def mostrar_tyc_dialog():
    st.markdown(config.TEXTO_LEGAL_COMPLETO)

def mostrar_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>⚽ Figus 26</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Tu álbum digital de intercambios</p>", unsafe_allow_html=True)
        
        # --- MODO RECUPERACIÓN DE CONTRASEÑA ---
        if st.session_state.get('modo_recuperacion', False):
            st.warning("🔐 Recuperar Cuenta")
            
            # Paso 1: Ingresar teléfono
            if 'recup_phone' not in st.session_state:
                phone_input = st.text_input("Ingresá tu celular:", placeholder="Ej: 2604123456")
                
                if st.button("Buscar Cuenta", use_container_width=True):
                    user_data, msg = db.get_security_info(phone_input)
                    if user_data:
                        st.session_state.recup_phone = phone_input
                        st.session_state.recup_question = user_data['secret_question']
                        st.session_state.recup_has_q = True if user_data['secret_question'] else False
                        st.rerun()
                    else:
                        st.error(msg)
                
                if st.button("🔙 Volver al Login"):
                    st.session_state.modo_recuperacion = False
                    st.rerun()
            
            # Paso 2: Responder pregunta de seguridad
            else:
                if not st.session_state.recup_has_q:
                    st.error("Esta cuenta no tiene configurada una pregunta de seguridad.")
                    st.info("Contactá al soporte con tu DNI en mano para blanquear la clave.")
                    st.link_button("💬 Contactar Soporte", "https://wa.me/5492604000000", type="primary")
                    if st.button("🔙 Volver"): 
                        del st.session_state.recup_phone
                        st.rerun()
                else:
                    st.info(f"Pregunta: **{st.session_state.recup_question}**")
                    ans = st.text_input("Tu Respuesta Secreta:", type="password")
                    new_pass = st.text_input("Nueva Contraseña:", type="password")
                    
                    if st.button("🔄 Cambiar Contraseña", type="primary", use_container_width=True):
                        ok, msg = db.reset_password(st.session_state.recup_phone, ans, new_pass)
                        if ok:
                            st.success(msg)
                            time.sleep(2)
                            del st.session_state.recup_phone
                            st.session_state.modo_recuperacion = False
                            st.rerun()
                        else:
                            st.error(msg)
                    
                    if st.button("Cancelar"):
                        del st.session_state.recup_phone
                        st.session_state.modo_recuperacion = False
                        st.rerun()

        # --- MODO LOGIN / REGISTRO NORMAL ---
        else:
            tab1, tab2 = st.tabs(["Ingresar", "Registrarse"])
            
            # Pestaña 1: Login
            with tab1:
                phone = st.text_input("Celular (sin 0 ni 15)", placeholder="Ej: 2604445566", key="l_phone")
                password = st.text_input("Contraseña", type="password", key="l_pass")
                
                if st.button("Ingresar", type="primary", use_container_width=True):
                    with utils.spinner_futbolero():
                        user, msg = db.login_user(phone, password)
                        time.sleep(1)
                    
                    if user:
                        st.session_state.user = user
                        
                        # --- PERSISTENCIA DE SESIÓN ---
                        token = utils.crear_token_sesion(user['id'])
                        st.query_params["token"] = token 
                        # ------------------------------

                        st.toast(f"¡Hola {user['nick']}!", icon="👋")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(msg)
                
                if st.button("¿Te olvidaste la contraseña?", type="secondary", use_container_width=True):
                    st.session_state.modo_recuperacion = True
                    st.rerun()

            # Pestaña 2: Registro
            with tab2:
                new_nick = st.text_input("Tu Apodo / Nick", placeholder="El 10", help="Debe ser único. Así te buscarán tus amigos.")
                new_phone = st.text_input("Celular", placeholder="Ej: 2604...", key="r_phone")
                
                c_prov, c_zone = st.columns(2)
                prov = c_prov.selectbox("Provincia", list(locations.ARGENTINA.keys()))
                zone = c_zone.selectbox("Zona", locations.ARGENTINA[prov])
                
                new_pass = st.text_input("Contraseña", type="password", key="r_pass")
                
                st.markdown("---")
                st.caption("🔐 **Seguridad (Para recuperar tu cuenta)**")
                secret_q = st.selectbox("Pregunta Secreta", [
                    "¿Cómo se llamaba tu primera mascota?",
                    "¿En qué calle vivías de niño?",
                    "¿Cuál es tu comida favorita?",
                    "¿Cuál fue tu primer recital?",
                    "¿Equipo de fútbol favorito?"
                ])
                secret_a = st.text_input("Respuesta Secreta", type="password", help="Acordate de esto, es la única forma de recuperar tu clave.")

                # TÉRMINOS Y CONDICIONES (CON BOTÓN POP-UP)
                st.markdown("---")
                if st.button("📄 Leer Términos y Condiciones", type="secondary", use_container_width=True):
                    mostrar_tyc_dialog()
                
                acepto_tyc = st.checkbox("He leído y acepto los Términos y Condiciones", key="chk_tyc")

                if st.button("Crear Cuenta", type="primary", use_container_width=True):
                    if not acepto_tyc:
                        st.error("⚠️ Debés aceptar los Términos y Condiciones para registrarte.")
                    else:
                        with utils.spinner_futbolero():
                            # Aquí se llama a database.py, que ahora verifica si el nick existe
                            user, msg = db.register_user(new_nick, new_phone, prov, zone, new_pass, secret_q, secret_a)
                        
                        if user:
                            st.success("¡Cuenta creada! Ya podés ingresar.")
                        else:
                            st.error(msg)