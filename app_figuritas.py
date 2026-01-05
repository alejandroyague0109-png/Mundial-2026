import streamlit as st
import pandas as pd
import time
from urllib.parse import quote
import config
import database as db

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    /* 0. ELIMINAR ENLACES DE TÍTULOS */
    .stHeading a { display: none !important; }
    [data-testid="stHeaderActionElements"] { display: none !important; }

    /* 1. SIDEBAR: Ancho (350px) y Compacto Verticalmente */
    section[data-testid="stSidebar"] {
        min-width: 350px !important;
        max-width: 350px !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    section[data-testid="stSidebar"] hr, 
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stButton,
    section[data-testid="stSidebar"] .stProgress 
    {
        margin-bottom: 0.5rem !important;
        margin-top: 0.2rem !important;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 2rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 2. FIGURITAS (Pills): Verde al seleccionar */
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #2e7d32 !important;
        border-color: #2e7d32 !important;
        color: white !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #2e7d32 !important;
        border-color: #2e7d32 !important;
        color: white !important;
    }

    /* 3. Botones secundarios redondeados */
    button[kind="secondary"] { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAR MEMORIA ---
if 'unlocked_users' not in st.session_state: st.session_state.unlocked_users = set()
if 'skip_security_modal' not in st.session_state: st.session_state.skip_security_modal = False

# --- CONSTANTES ---
ZONAS_DISPONIBLES = ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"]

# --- MODALES ---

@st.dialog("🛡️ Consejos de Seguridad")
def modal_seguridad(target_id):
    st.markdown("### ⚠️ Antes de contactar:")
    st.info("Para realizar un intercambio seguro, te recomendamos:")
    st.markdown("""
    * 🏢 **Lugar Público:** Reúnete siempre en zonas concurridas.
    * 👀 **Verificación:** Revisa las figuritas antes de entregar las tuyas.
    * 💰 **Dinero:** No envíes dinero por adelantado.
    """)
    st.divider()
    st.caption("Al confirmar, usarás 1 crédito diario (si no eres Premium) para ver el teléfono.")
    
    no_volver_a_mostrar = st.checkbox("No volver a mostrar este mensaje", key="chk_skip_sec")
    
    if st.button("✅ Entendido, Ver Contacto", type="primary", use_container_width=True):
        if no_volver_a_mostrar:
            st.session_state.skip_security_modal = True
            
        if db.check_contact_limit(st.session_state.user):
            db.consume_credit(st.session_state.user)
            st.session_state.unlocked_users.add(target_id)
            st.rerun()
        else:
            st.error("Error: No tienes créditos suficientes.")

@st.dialog("💎 Pásate a Premium", width="small")
def mostrar_modal_premium():
    st.markdown(f"""
    ### 🚀 Límite Alcanzado
    Tienes **1 contacto gratis por día**.
    
    **Con Premium obtienes:**
    * 🔓 **Ilimitado:** Contacta sin restricciones.
    * 📐 **Triangulaciones:** Acceso a cadenas de cambio.
    * 🌍 **Un pago único:** Todo el mundial.
    * ⭐ **Destacado:** Perfil verificado.
    
    ---
    ### Precio Final: **${config.PRECIO_PREMIUM}**
    """)
    st.link_button("👉 Pagar con Mercado Pago", config.MP_LINK, type="primary", use_container_width=True)
    st.caption("Luego pega tu ID de operación en el menú lateral.")

@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes. No nos hacemos responsables de las reuniones pactadas por los usuarios ni de las transacciones realizadas.")
    st.markdown("**Al continuar, declaras bajo juramento que eres mayor de edad.**")
    
    if st.button("✅ Entendido, soy +18", type="primary", use_container_width=True):
        st.session_state.barrera_superada = True
        st.rerun()

@st.dialog("📄 Términos", width="large")
def ver_contrato(): st.markdown(config.TEXTO_LEGAL_COMPLETO)

@st.dialog("📤 Ayuda CSV")
def mostrar_instrucciones_csv():
    st.markdown("""
    ### Formato del Archivo
    Debe tener 3 columnas obligatorias:
    1. **num**: Número de la figurita (ej: 10, 150).
    2. **status**: Escribe `tengo` o `repetida`.
    3. **price**: Precio de venta (0 si es para canje).
    *(Opcional: 'quantity')*
    """)

# --- LOGIN / REGISTRO ---
if 'barrera_superada' not in st.session_state: st.session_state.barrera_superada = False
if not st.session_state.barrera_superada: mostrar_barrera_entrada()
is_locked = not st.session_state.barrera_superada

if 'user' not in st.session_state: st.session_state.user = None
if not st.session_state.user:
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    with t1:
        p = st.text_input("Teléfono", key="l_p")
        pw = st.text_input("Contraseña", type="password", key="l_pw")
        if st.button("Entrar", type="primary", disabled=is_locked):
            u, m = db.login_user(p, pw)
            if u: st.session_state.user = u; st.rerun()
            else: st.error(m)
    with t2:
        n = st.text_input("Nick"); ph = st.text_input("Teléfono", key="r_p"); pw2 = st.text_input("Crear Pass", type="password", key="r_pw")
        z = st.selectbox("Zona", ZONAS_DISPONIBLES)
        st.divider()
        if st.button("Legales", type="secondary"): ver_contrato()
        acepto = st.checkbox("Acepto términos")
        if st.button("Crear Cuenta", disabled=(is_locked or not acepto)):
            u, m = db.register_user(n, ph, z, pw2)
            if u: st.success("Creado!"); st.balloons()
            else: st.error(m)
    st.stop()

user = st.session_state.user

# --- VERIFICACIÓN DIARIA (RESET) ---
if db.verify_daily_reset(user):
    st.session_state.unlocked_users = set()
    st.toast("📅 ¡Nuevo día! Tus contactos diarios se han renovado.", icon="☀️")

# --- CÁLCULOS ---
seleccion_pais = st.session_state.get("seleccion_pais_key", list(config.ALBUM_PAGES.keys())[0])
start, end = config.ALBUM_PAGES[seleccion_pais]
total_active = end - start + 1
total_album = sum([(v[1] - v[0] + 1) for v in config.ALBUM_PAGES.values()])

ids_tengo_db, repetidas_info, df_full = db.get_inventory_status(user['id'], start, end)
key_pills = f"pills_tengo_{seleccion_pais}"
ids_tengo_live = st.session_state.get(key_pills, ids_tengo_db)

try: tengo_db_total = df_full[df_full['status'] == 'tengo'].shape[0]
except: tengo_db_total = 0
tengo_db_esta_seccion = len(ids_tengo_db)
tengo_live_count = len(ids_tengo_live)
tengo_global_live = (tengo_db_total - tengo_db_esta_seccion) + tengo_live_count

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    st.caption(f"⭐ Reputación: {user.get('reputation', 0)}")
    
    st.divider()
    progreso = min(tengo_global_live / total_album, 1.0)
    st.progress(progreso, text="🏆 Mi Álbum")
    st.caption(f"Tienes **{tengo_global_live}** de {total_album}.")
    
    st.divider()
    with st.expander("📤 Carga Masiva (CSV)"):
        st.caption("Carga rápida de inventario.")
        col_a, col_b = st.columns(2)
        if col_a.button("❓ Ayuda", use_container_width=True): mostrar_instrucciones_csv()
        df_plantilla = pd.DataFrame([{"num": 10, "status": "tengo", "price": 0, "quantity": 1}, {"num": 25, "status": "repetida", "price": 500, "quantity": 2}])
        csv_plantilla = df_plantilla.to_csv(index=False).encode('utf-8')
        col_b.download_button("⬇️ Plantilla", data=csv_plantilla, file_name="plantilla.csv", mime="text/csv", use_container_width=True)
        up = st.file_uploader("Subir CSV", type="csv")
        if up and st.button("🚀 Procesar Carga", type="primary", use_container_width=True):
            ok, msg = db.process_csv_upload(pd.read_csv(up), user['id'])
            if ok: st.success(msg); time.sleep(2); st.rerun()
            else: st.error(msg)
            
    st.divider()
    if user.get('is_premium', False):
        st.success("💎 PREMIUM")
    else:
        st.info("👤 GRATIS")
        contacts = user.get('daily_contacts_count', 0)
        if contacts >= 1: st.progress(1.0, text="Límite: 1/1 (Agotado)")
        else: st.progress(0.0, text="Límite: 0/1 (Disponible)")
        if st.button("💎 Ser Premium", use_container_width=True): mostrar_modal_premium()
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

st.markdown("### 1️⃣ Tus Figuritas")
seleccion_tengo = st.pills("Tengo", list(range(start, end + 1)), default=ids_tengo_live, selection_mode="multi", key=key_pills)

st.markdown("### 2️⃣ Repetidas")
posibles_repes = sorted(seleccion_tengo) if seleccion_tengo else []
ids_repes_val = [k for k in repetidas_info.keys() if k in posibles_repes]
seleccion_repes = st.pills("Repetidas", posibles_repes, default=ids_repes_val, selection_mode="multi", key=f"repes_{seleccion_pais}")

if seleccion_repes:
    st.info("👇 **Tip:** Doble clic en 'Modo' para cambiar entre **Canje** y **Venta**. Ajusta la 'Cantidad'.")
    data = []
    for n in seleccion_repes:
        info = repetidas_info.get(n, {})
        precio = info.get('price', 0)
        qty = info.get('quantity', 1)
        modo = "💰 Venta" if precio > 0 else "🔄 Canje"
        data.append({"Figurita": n, "Cantidad": qty, "Modo": modo, "Precio": precio})
        
    edited_df = st.data_editor(
        pd.DataFrame(data), 
        column_config={
            "Figurita": st.column_config.NumberColumn(disabled=True),
            "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, help="Copias disponibles"),
            "Modo": st.column_config.SelectboxColumn(options=["🔄 Canje", "💰 Venta"], required=True),
            "Precio": st.column_config.NumberColumn(min_value=0, step=100)
        }, 
        hide_index=True, use_container_width=True
    )
    
    if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
        db.save_inventory_positive(user['id'], start, end, seleccion_tengo, edited_df)
        st.toast("Guardado", icon="✅"); time.sleep(0.5); st.rerun()

# --- MERCADO ---
st.divider()
st.subheader("🔍 Mercado")

with st.expander("🔎 Filtros de Búsqueda", expanded=True):
    col_f1, col_f2 = st.columns(2)
    filtro_zonas = col_f1.multiselect("Filtrar por Zona:", ZONAS_DISPONIBLES, default=[user['zone']])
    filtro_num = col_f2.text_input("Buscar Figurita #:", placeholder="Ej: 10")

market_df = db.fetch_market(user['id'])
matches, ventas = db.find_matches(user['id'], market_df)

def aplicar_filtros(lista_items):
    filtrados = []
    for item in lista_items:
        if filtro_zonas and item['zone'] not in filtro_zonas: continue
        if filtro_num and str(item['figu']) != filtro_num: continue
        filtrados.append(item)
    return filtrados

matches_filtrados = aplicar_filtros(matches)
ventas_filtradas = aplicar_filtros(ventas)

t1, t2 = st.tabs([f"Canjes ({len(matches_filtrados)})", f"Ventas ({len(ventas_filtradas)})"])

def render_card(item, tipo):
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        target_id = item['target_id']
        fig_recibo = item['figu']
        
        phone_target = item['phone']
        if tipo == 'canje':
            fig_entrego = item['te_pide']
            texto_base = f"Hola! Vi en Figus 26 que cambias la figurita #{fig_recibo} por la #{fig_entrego}. ¿Hacemos canje?"
            c1.markdown(f"🔄 **{item['nick']}** ({item['zone']}) cambia **#{fig_recibo}** por tu **#{fig_entrego}**")
        else:
            precio = item['price']
            texto_base = f"Hola! Vi en Figus 26 que vendes la figurita #{fig_recibo} a ${precio}. ¿La tienes disponible?"
            c1.markdown(f"💰 **{item['nick']}** ({item['zone']}) vende **#{fig_recibo}** a **${precio}**")

        mensaje_encoded = quote(texto_base)
        link_wa = f"https://wa.me/549{phone_target}?text={mensaje_encoded}"

        is_unlocked = target_id in st.session_state.unlocked_users
        
        if is_unlocked:
            c2.link_button("🟢 Abrir Chat", link_wa, use_container_width=True)
            if tipo == 'canje':
                with c1.expander("⚙️ Confirmar Canje"):
                    st.caption("Solo si ya realizaste el intercambio:")
                    if st.button(f"✅ Registrar #{fig_recibo}", key=f"swap_{fig_recibo}_{target_id}"):
                        ok, msg = db.register_exchange(user['id'], fig_entrego, fig_recibo)
                        if ok: st.balloons(); st.success(msg); time.sleep(3); st.rerun()
                        else: st.error(msg)
        else:
            if c2.button("🔓 Contactar", key=f"ul_{tipo}_{fig_recibo}_{target_id}", use_container_width=True):
                if db.check_contact_limit(user):
                    if st.session_state.skip_security_modal:
                        db.consume_credit(user)
                        st.session_state.unlocked_users.add(target_id)
                        st.rerun()
                    else:
                        modal_seguridad(target_id)
                else: 
                     mostrar_modal_premium()
        
        if c3.button("👍", key=f"vt_{tipo}_{fig_recibo}_{target_id}"):
            ok, m = db.votar_usuario(user['id'], target_id)
            st.toast(m)

with t1:
    if not matches_filtrados: st.info("No hay canjes con estos filtros.")
    for m in matches_filtrados: render_card(m, 'canje')
with t2:
    if not ventas_filtradas: st.info("No hay ventas con estos filtros.")
    for v in ventas_filtradas: render_card(v, 'venta')