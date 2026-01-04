import streamlit as st
import pandas as pd
import time
# --- IMPORTAMOS NUESTROS MÓDULOS ---
import config
import database as db

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# Inyección de estilos CSS
st.markdown("""
    <style>
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #2e7d32 !important; color: white !important; border-color: #2e7d32 !important;
    }
    div[data-testid="stPills"] span:hover, div[data-testid="stPills"] button:hover {
        border-color: #66bb6a !important; color: #2e7d32 !important;
    }
    button[kind="secondary"] { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- MODALES ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto, pero no intervenimos en los canjes.")
    st.markdown("**Al continuar, declaras que eres mayor de edad.**")
    if st.button("✅ Entendido, soy +18", type="primary", use_container_width=True):
        st.session_state.barrera_superada = True
        st.rerun()

@st.dialog("📄 Términos y Condiciones", width="large")
def ver_contrato():
    st.markdown(config.TEXTO_LEGAL_COMPLETO)

# --- INICIO DE SESIÓN / REGISTRO ---
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False
if not st.session_state.barrera_superada: mostrar_barrera_entrada()

if 'user' not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    
    with t1:
        p = st.text_input("Teléfono"); pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar", type="primary"):
            u, m = db.login_user(p, pw)
            if u: st.session_state.user = u; st.rerun()
            else: st.error(m)
            
    with t2:
        st.caption("Crea tu cuenta.")
        n = st.text_input("Nick"); ph = st.text_input("Teléfono"); passw = st.text_input("Crear Pass", type="password")
        z = st.selectbox("Zona", ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"])
        st.divider()
        if st.button("📖 Leer Términos", type="secondary"): ver_contrato()
        acepto = st.checkbox("Acepto los Términos.")
        if st.button("Crear Cuenta", disabled=not acepto):
            u, m = db.register_user(n, ph, z, passw)
            if u: st.success("Creado!"); st.balloons()
            else: st.error(m)
    st.stop()

user = st.session_state.user

# --- LÓGICA DE PROGRESO ---
seleccion_pais = st.session_state.get("seleccion_pais_key", list(config.ALBUM_PAGES.keys())[0])
start, end = config.ALBUM_PAGES[seleccion_pais]
total_active = end - start + 1
total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])

ids_tengo_db, repetidas_info, df_full = db.get_inventory_status(user['id'], start, end)
key_pills = f"pills_tengo_{seleccion_pais}"
ids_tengo_live = st.session_state.get(key_pills, ids_tengo_db)

tengo_live_count = len(ids_tengo_live)
try: tengo_db_total = df_full[df_full['status'] == 'tengo'].shape[0]
except: tengo_db_total = 0
tengo_db_esta_seccion = len(ids_tengo_db)
tengo_global_live = (tengo_db_total - tengo_db_esta_seccion) + tengo_live_count

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
    
    if user['is_admin']: # Usamos el campo is_admin de la DB
        st.info("🕵️ ADMIN")
        with st.expander("📤 Carga Masiva"):
            up = st.file_uploader("CSV", type="csv")
            if up and st.button("Procesar"):
                ok, msg = db.admin_process_csv(pd.read_csv(up), user['id'])
                if ok: st.success(msg)
                else: st.error(msg)
    
    st.divider()
    st.progress(min(tengo_global_live / total_album, 1.0), text="Álbum Completo")
    st.caption(f"Tienes **{tengo_global_live}** de {total_album}.")
    st.divider()

    if user['is_premium']: st.success("💎 PREMIUM")
    else: 
        st.warning("👤 GRATIS")
        st.link_button("👉 Activar Premium", config.MP_LINK)
        if st.button("Validar Pago"):
            op = st.text_input("ID Op", key="op_v")
            if op and st.button("OK"):
                exito, msg = db.verificar_pago_mp(op, user['id'])
                if exito: st.success(msg); time.sleep(2); st.rerun()
    
    if st.button("Salir"): st.session_state.user = None; st.rerun()

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum")
seleccion = st.selectbox("Sección:", list(config.ALBUM_PAGES.keys()), key="seleccion_pais_key")
st.progress(min(tengo_live_count / total_active, 1.0), text=f"Sección {seleccion}")

st.divider()
st.markdown("### 1️⃣ ¿Cuáles TENÉS? (Verde ✅)")
seleccion_tengo = st.pills("Tengo", list(range(start, end + 1)), default=ids_tengo_live, selection_mode="multi", key=key_pills)

st.markdown("### 2️⃣ ¿Cuáles REPETISTE?")
posibles_repetidas = sorted(seleccion_tengo) if seleccion_tengo else []
ids_validos = [k for k in repetidas_info.keys() if k in posibles_repetidas]
seleccion_repes = st.pills("Repetidas", posibles_repetidas, default=ids_validos, selection_mode="multi", key=f"pills_repes_{seleccion}")

edited_df = pd.DataFrame()
if seleccion_repes:
    st.caption("💲 Precios")
    data = [{"Figurita": n, "Modo": "Venta" if repetidas_info.get(n,{}).get('price',0)>0 else "Canje", "Precio": repetidas_info.get(n,{}).get('price',0)} for n in seleccion_repes]
    edited_df = st.data_editor(pd.DataFrame(data), column_config={
        "Figurita": st.column_config.NumberColumn(disabled=True),
        "Modo": st.column_config.SelectboxColumn(options=["Canje", "Venta"], required=True),
        "Precio": st.column_config.NumberColumn(min_value=0, step=100)
    }, hide_index=True, use_container_width=True, key=f"editor_{seleccion}")

st.markdown("---")
if st.button("💾 GUARDAR", type="primary", use_container_width=True):
    db.save_inventory_positive(user['id'], start, end, seleccion_tengo, edited_df)
    st.toast("¡Guardado!", icon="✅"); time.sleep(1); st.rerun()

st.divider()
st.subheader("🔍 Mercado")
market_df = db.fetch_market(user['id'])
matches, ventas = db.find_matches(user['id'], market_df)

t1, t2 = st.tabs([f"Canjes ({len(matches)})", f"Ventas ({len(ventas)})"])

with t1:
    if not matches: st.info("Sin canjes.")
    for m in matches:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"🔄 **{m['nick']}** (⭐{m['reputation']}) cambia **#{m['figu']}** por tu **#{m['te_pide']}**")
            if c2.button("WhatsApp", key=f"c_{m['figu']}_{m['target_id']}"):
                if db.check_contact_limit(user): db.consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{m['phone']})")
                else: st.error("Límite diario.")
            if c3.button("👍", key=f"v_{m['target_id']}_{m['figu']}"):
                ok, msg = db.votar_usuario(user['id'], m['target_id'])
                st.toast(msg)

with t2:
    if not ventas: st.info("Sin ventas.")
    for v in ventas:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"💰 **{v['nick']}** (⭐{v['reputation']}) vende **#{v['figu']}** a **${v['price']}**")
            if c2.button("WhatsApp", key=f"ve_{v['figu']}_{v['target_id']}"):
                if db.check_contact_limit(user): db.consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{v['phone']})")
                else: st.error("Límite diario.")
            if c3.button("👍", key=f"vv_{v['target_id']}_{v['figu']}"):
                ok, msg = db.votar_usuario(user['id'], v['target_id'])
                st.toast(msg)