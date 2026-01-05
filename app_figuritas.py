import streamlit as st
import pandas as pd
import time
import config
import database as db

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# Estilos CSS
st.markdown("""
    <style>
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important;
    }
    button[kind="secondary"] { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR MEMORIA DE CONTACTOS DESBLOQUEADOS ---
if 'unlocked_users' not in st.session_state:
    st.session_state.unlocked_users = set()

# --- MODALES ---
@st.dialog("💎 Pásate a Premium", width="small")
def mostrar_modal_premium():
    st.markdown(f"""
    ### 🚀 Límite Alcanzado
    Tienes **1 contacto gratis por día**.
    
    **Con Premium obtienes:**
    * 🔓 Contactos Ilimitados
    * 🌍 Un pago único (todo el mundial)
    
    ### Precio: **${config.PRECIO_PREMIUM}**
    """)
    st.link_button("👉 Pagar con Mercado Pago", config.MP_LINK, type="primary", use_container_width=True)
    st.caption("Luego pega tu ID de operación en el menú lateral.")

@st.dialog("⚠️ Bienvenido")
def mostrar_barrera_entrada():
    st.warning("🔞 App para mayores de 18 años.")
    st.info("No nos hacemos responsables de las reuniones pactadas.")
    if st.button("✅ Entendido, soy +18", type="primary", use_container_width=True):
        st.session_state.barrera_superada = True
        st.rerun()

@st.dialog("📄 Términos", width="large")
def ver_contrato():
    st.markdown(config.TEXTO_LEGAL_COMPLETO)

@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("Columnas: **num**, **status** (tengo/repetida), **price**.")

# --- LOGIN / REGISTRO ---
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False
if not st.session_state.barrera_superada: mostrar_barrera_entrada()

if 'user' not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    
    with t1:
        p = st.text_input("Teléfono", key="login_tel")
        pw = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar", type="primary"):
            u, m = db.login_user(p, pw)
            if u: 
                st.session_state.user = u
                st.rerun()
            else: st.error(m)
    with t2:
        n = st.text_input("Nick")
        ph = st.text_input("Teléfono", key="reg_tel")
        pw2 = st.text_input("Pass", type="password", key="reg_pass")
        z = st.selectbox("Zona", ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"])
        st.divider()
        if st.button("Legales", type="secondary"): ver_contrato()
        acepto = st.checkbox("Acepto términos")
        if st.button("Crear Cuenta", disabled=not acepto):
            u, m = db.register_user(n, ph, z, pw2)
            if u: st.success("Creado!"); st.balloons()
            else: st.error(m)
    st.stop()

user = st.session_state.user

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
    
    # Panel Admin
    if user.get('is_admin', False):
        st.divider()
        st.info("🕵️ ADMIN")
    
    # Carga Masiva
    with st.expander("📤 Carga Masiva"):
        if st.button("❓ Ayuda"): mostrar_instrucciones_csv()
        up = st.file_uploader("CSV", type="csv")
        if up and st.button("Procesar"):
            ok, msg = db.process_csv_upload(pd.read_csv(up), user['id'])
            if ok: st.success(msg); time.sleep(2); st.rerun()
            else: st.error(msg)
            
    st.divider()
    # Estado Premium
    if user.get('is_premium', False):
        st.success("💎 PREMIUM")
    else:
        st.info("👤 GRATIS")
        contacts = user.get('daily_contacts_count', 0)
        st.progress(min(contacts, 1.0), f"Usado hoy: {contacts}/1")
        if st.button("💎 Ser Premium"): mostrar_modal_premium()
        
        with st.expander("Validar Pago"):
            op = st.text_input("ID Op")
            if op and st.button("Validar"):
                ok, msg = db.verificar_pago_mp(op, user['id'])
                if ok: st.success(msg); time.sleep(2); st.rerun()
                else: st.error(msg)

    if st.button("Salir"): st.session_state.user = None; st.rerun()

# --- APP PRINCIPAL ---
st.header("📖 Mi Álbum")
seleccion_pais = st.selectbox("Sección:", list(config.ALBUM_PAGES.keys()), key="seleccion_pais_key")
start, end = config.ALBUM_PAGES[seleccion_pais]

# Inventario
ids_tengo_db, repetidas_info, df_full = db.get_inventory_status(user['id'], start, end)
key_pills = f"pills_tengo_{seleccion_pais}"
ids_tengo_live = st.session_state.get(key_pills, ids_tengo_db)

# Guardado
st.markdown("### 1️⃣ Tus Figuritas")
seleccion_tengo = st.pills("Tengo", list(range(start, end + 1)), default=ids_tengo_live, selection_mode="multi", key=key_pills)
st.markdown("### 2️⃣ Repetidas")
posibles_repes = sorted(seleccion_tengo) if seleccion_tengo else []
ids_repes_val = [k for k in repetidas_info.keys() if k in posibles_repes]
seleccion_repes = st.pills("Repetidas", posibles_repes, default=ids_repes_val, selection_mode="multi", key=f"repes_{seleccion_pais}")

edited_df = pd.DataFrame()
if seleccion_repes:
    data = [{"Figurita": n, "Modo": "Venta" if repetidas_info.get(n,{}).get('price',0)>0 else "Canje", "Precio": repetidas_info.get(n,{}).get('price',0)} for n in seleccion_repes]
    edited_df = st.data_editor(pd.DataFrame(data), hide_index=True, use_container_width=True)

if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
    db.save_inventory_positive(user['id'], start, end, seleccion_tengo, edited_df)
    st.toast("Guardado", icon="✅")
    time.sleep(0.5)
    st.rerun()

# --- MERCADO ---
st.divider()
st.subheader("🔍 Mercado")
market_df = db.fetch_market(user['id'])
matches, ventas = db.find_matches(user['id'], market_df)

t1, t2 = st.tabs([f"Canjes ({len(matches)})", f"Ventas ({len(ventas)})"])

def render_market_card(item, type_card):
    """Función auxiliar para dibujar tarjetas"""
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        
        # Texto
        if type_card == 'canje':
            c1.markdown(f"🔄 **{item['nick']}** (⭐{item['reputation']}) cambia **#{item['figu']}** por tu **#{item['te_pide']}**")
        else:
            c1.markdown(f"💰 **{item['nick']}** (⭐{item['reputation']}) vende **#{item['figu']}** a **${item['price']}**")
        
        # LÓGICA DE DESBLOQUEO (EL CAMBIO CLAVE)
        target_id = item['target_id']
        is_unlocked = target_id in st.session_state.unlocked_users
        
        # Botón Central
        if is_unlocked:
            # Si ya pagó el crédito, mostramos el link directo verde
            c2.link_button("🟢 Abrir Chat", f"https://wa.me/549{item['phone']}", use_container_width=True)
        else:
            # Si no, mostramos botón de desbloqueo
            if c2.button("🔓 Contactar", key=f"unlock_{type_card}_{item['figu']}_{target_id}", use_container_width=True):
                # Verificamos límite AQUÍ
                if db.check_contact_limit(user):
                    db.consume_credit(user)
                    st.session_state.unlocked_users.add(target_id) # Recordar desbloqueo
                    st.rerun() # Recargar para mostrar el botón verde
                else:
                    mostrar_modal_premium()
        
        # Botón Reputación
        if c3.button("👍", key=f"vote_{type_card}_{item['figu']}_{target_id}"):
            ok, msg = db.votar_usuario(user['id'], target_id)
            st.toast(msg)

with t1:
    if not matches: st.info("No hay canjes directos.")
    for m in matches: render_market_card(m, 'canje')

with t2:
    if not ventas: st.info("No hay ventas.")
    for v in ventas: render_market_card(v, 'venta')