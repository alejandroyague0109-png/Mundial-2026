import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago
import bcrypt
import re

# --- CONFIGURACIÓN E INYECCIÓN DE ESTILO (VERDE FORZADO) ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

st.markdown(
    """
    <style>
    /* Forzar color VERDE en Píldoras Seleccionadas */
    /* Selector genérico para versiones recientes de Streamlit */
    div[data-testid="stPills"] span[aria-selected="true"] {
        background-color: #2e7d32 !important;
        color: white !important;
        border-color: #2e7d32 !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background-color: #2e7d32 !important;
        color: white !important;
        border-color: #2e7d32 !important;
    }
    /* Eliminar el borde rojo por defecto al hacer hover */
    div[data-testid="stPills"] span:hover, div[data-testid="stPills"] button:hover {
        border-color: #66bb6a !important;
        color: #2e7d32 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 🛠️ DATOS SEGUROS ---
try:
    ADMIN_PHONE = st.secrets["ADMIN_PHONE"]
    PRECIO_PREMIUM = 5000 
    MP_LINK = "https://link.mercadopago.com.ar/..." 
    
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    mp_token = st.secrets["MP_ACCESS_TOKEN"]
    
    supabase: Client = create_client(url, key)
    sdk = mercadopago.SDK(mp_token)
except Exception as e:
    st.error(f"Error de configuración: {e}")
    st.stop()

ALBUM_PAGES = {
    "FW - Intro / Museos": (1, 19),
    "ARG - Argentina": (20, 39),
    "BRA - Brasil": (40, 59),
    "FRA - Francia": (60, 79),
    "USA - Estados Unidos": (80, 99),
    "MEX - México": (100, 119),
    "CAN - Canadá": (120, 139),
    "ESP - España": (140, 159),
    "Especiales Coca-Cola": (600, 608)
}

# --- FUNCIONES CORE ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_text, hashed_text):
    try: return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_text.encode('utf-8'))
    except: return False

def validar_telefono(phone):
    return bool(re.match(r"^\d{10,13}$", phone))

def login_user(phone, password):
    response = supabase.table("users").select("*").eq("phone", phone).execute()
    if not response.data: return None, "Usuario no encontrado."
    user = response.data[0]
    if check_password(password, user['password']): return user, "OK"
    else: return None, "Contraseña incorrecta."

def register_user(nick, phone, zone, password):
    if not validar_telefono(phone): return None, "Teléfono inválido."
    if supabase.table("users").select("*").eq("phone", phone).execute().data: return None, "Teléfono ya existe."
    try:
        hashed_pw = hash_password(password)
        data = {"nick": nick, "phone": phone, "zone": zone, "password": hashed_pw, "is_admin": (phone == ADMIN_PHONE)}
        response = supabase.table("users").insert(data).execute()
        return response.data[0], "OK"
    except Exception as e: return None, str(e)

def verificar_pago_mp(payment_id, user_id):
    try:
        if supabase.table("payments_log").select("*").eq("payment_id", payment_id).execute().data:
            return False, "Comprobante ya usado."
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 404: return False, "ID no encontrado."
        resp = payment_info["response"]
        if resp.get("status") == "approved" and resp.get("transaction_amount") >= PRECIO_PREMIUM:
            supabase.table("payments_log").insert({
                "payment_id": str(payment_id), "user_id": user_id, "amount": resp.get("transaction_amount"), "status": "approved"
            }).execute()
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Premium Activado!"
        else: return False, "Pago no aprobado."
    except Exception as e: return False, str(e)

# --- 🧠 LÓGICA INTELIGENTE DE DATOS ---

def get_inventory_status(user_id, start, end):
    """Trae datos de la BD para inicializar la vista"""
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    numeros_rango = list(range(start, end + 1))
    db_faltantes = []
    db_repetidas_info = {}
    
    if not df.empty:
        # Filtramos solo lo relevante para esta página
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        db_faltantes = df_page[df_page['status'] == 'faltante']['sticker_num'].tolist()
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            db_repetidas_info[row['sticker_num']] = {'price': row['price']}
    
    # Si no hay datos, asumimos vacío (para que marque)
    has_data = not df[ (df['sticker_num'] >= start) & (df['sticker_num'] <= end) ].empty
    if not has_data: ids_que_tengo = []
    else: ids_que_tengo = [n for n in numeros_rango if n not in db_faltantes]

    return ids_que_tengo, db_repetidas_info, df # Devolvemos df completo para cálculos globales

def save_inventory_inverted(user_id, start, end, ui_owned_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    new_rows = []
    # Guardar Faltantes (Lo que NO tiene)
    ids_faltantes = [n for n in page_numbers if n not in ui_owned_list]
    for num in ids_faltantes:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "faltante", "price": 0})
    
    # Guardar Repetidas
    if not ui_repe_df.empty:
        for _, row in ui_repe_df.iterrows():
            new_rows.append({
                "user_id": user_id, 
                "sticker_num": row['Figurita'], 
                "status": "repetida", 
                "price": int(row['Precio']) if row['Modo'] == "Venta" else 0
            })
    if new_rows: supabase.table("inventory").insert(new_rows).execute()

def fetch_market(user_id):
    resp = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", user_id).execute()
    return pd.DataFrame(resp.data)

def find_matches(user_id, market_df):
    resp = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    mi_df = pd.DataFrame(resp.data)
    if mi_df.empty: return [], []
    
    mis_f = mi_df[mi_df['status'] == 'faltante']['sticker_num'].tolist()
    mis_r = mi_df[mi_df['status'] == 'repetida']['sticker_num'].tolist()
    
    directos, ventas = [], []
    if market_df.empty: return [], []
    
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    
    ofertas = market_df[(market_df['status'] == 'repetida') & (market_df['sticker_num'].isin(mis_f))]
    for _, row in ofertas.iterrows():
        match = {'nick': row['nick'], 'zone': row['zone'], 'phone': row['phone'], 'figu': row['sticker_num'], 'price': row['price']}
        if row['price'] > 0: ventas.append(match)
        else:
            sus_faltas = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'faltante')]['sticker_num'].tolist()
            if set(mis_r).intersection(set(sus_faltas)):
                match['te_pide'] = list(set(mis_r).intersection(set(sus_faltas)))[0]
                directos.append(match)
    return directos, ventas

def check_contact_limit(user):
    if user['is_premium']: return True
    if str(user['last_contact_date']) != str(date.today()):
        supabase.table("users").update({"last_contact_date": str(date.today()), "daily_contacts_count": 0}).eq("id", user['id']).execute()
        return True
    return user['daily_contacts_count'] < 1

def consume_credit(user):
    if not user['is_premium']:
        nuevo = user['daily_contacts_count'] + 1
        supabase.table("users").update({"daily_contacts_count": nuevo}).eq("id", user['id']).execute()
        st.session_state.user['daily_contacts_count'] = nuevo

# --- UI PRINCIPAL ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    with t1:
        p = st.text_input("Teléfono"); pw = st.text_input("Pass", type="password")
        if st.button("Entrar"):
            u, m = login_user(p, pw)
            if u: st.session_state.user = u; st.rerun()
            else: st.error(m)
    with t2:
        n = st.text_input("Nick"); ph = st.text_input("Tel (ID)"); passw = st.text_input("Crear Pass", type="password")
        z = st.selectbox("Zona", ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"])
        if st.button("Crear"):
            u, m = register_user(n, ph, z, passw)
            if u: st.success("Creado!"); st.rerun()
            else: st.error(m)
    st.stop()

user = st.session_state.user

# --- CÁLCULO DE PROGRESO DINÁMICO (LA MAGIA) ---
# Aquí calculamos el progreso combinando BD + Lo que estás tocando ahora mismo en pantalla

# 1. Recuperar selección actual del usuario (país activo)
seleccion_pais = st.session_state.get("seleccion_pais_key", list(ALBUM_PAGES.keys())[0])
start_active, end_active = ALBUM_PAGES[seleccion_pais]
total_active = end_active - start_active + 1

# Recuperamos lo que tiene en BD para inicializar
ids_tengo_db, repetidas_info, df_full = get_inventory_status(user['id'], start_active, end_active)

# VERIFICAR SI HAY CAMBIOS EN VIVO (Session State)
# Si el usuario tocó las pildoras, usamos ese valor. Si no, usamos DB.
key_pills = f"pills_tengo_{seleccion_pais}"
if key_pills in st.session_state:
    ids_tengo_live = st.session_state[key_pills]
else:
    ids_tengo_live = ids_tengo_db

tengo_live_count = len(ids_tengo_live)

# 2. Calcular Progreso Global Dinámico
# Total del álbum
total_album = sum([(v[1] - v[0] + 1) for v in ALBUM_PAGES.values()])

# Cuántas tengo en TOTAL (Sumamos las de la BD de OTROS países + las LIVE de este país)
# Filtramos del DF full todo lo que NO sea de este país y que NO sea faltante
df_otros = df_full[~((df_full['sticker_num'] >= start_active) & (df_full['sticker_num'] <= end_active))]
# En BD guardamos faltantes, así que Tengo_Otros = Total_Otros - Faltantes_Otros
# (Simplificación: Asumimos que lo que no está en 'faltante' lo tiene, para mantener lógica)
# Para hacerlo robusto: Contamos faltantes globales en BD
faltantes_db_total = df_full[df_full['status'] == 'faltante'].shape[0]
# Restamos las faltantes de este país según BD (porque las reemplazaremos con las live)
faltantes_db_este_pais = df_full[(df_full['status'] == 'faltante') & (df_full['sticker_num'] >= start_active) & (df_full['sticker_num'] <= end_active)].shape[0]

faltantes_reales_otros = faltantes_db_total - faltantes_db_este_pais
faltantes_live_este_pais = total_active - tengo_live_count

faltantes_totales_live = faltantes_reales_otros + faltantes_live_este_pais
tengo_total_live = total_album - faltantes_totales_live

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    if user['phone'] == ADMIN_PHONE: st.info("🕵️ ADMIN")
    
    st.divider()
    # BARRA GLOBAL DINÁMICA
    progreso_global = min(tengo_total_live / total_album, 1.0)
    st.progress(progreso_global, text="Tu Álbum Completo")
    st.caption(f"Tienes **{tengo_total_live}** de {total_album} figuritas.")
    
    st.divider()
    if user['is_premium']: st.success("💎 PREMIUM")
    else: 
        st.warning("👤 GRATIS")
        st.link_button("👉 Activar Premium", MP_LINK)
        if st.button("Validar Pago"):
            st.info("Pega tu ID de operación:")
            op = st.text_input("ID", key="op_id")
            if op and st.button("Confirmar"):
                exito, msg = verificar_pago_mp(op, user['id'])
                if exito: st.success(msg); time.sleep(2); st.rerun()
    if st.button("Salir"): st.session_state.user = None; st.rerun()

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum")

# Selector de país con KEY para que podamos leerlo en el sidebar
seleccion = st.selectbox("Selecciona Sección:", list(ALBUM_PAGES.keys()), key="seleccion_pais_key")

# BARRA LOCAL DINÁMICA
progreso_local = min(tengo_live_count / total_active, 1.0)
st.progress(progreso_local, text=f"Sección {seleccion}: Tienes {tengo_live_count} de {total_active}")

st.divider()

# --- INTERFAZ REACTIVA ---
st.markdown("### 1️⃣ ¿Cuáles TENÉS? (Verde ✅)")
# Widget Pills: Al tocar aquí, se actualiza el session_state y la barra de arriba cambia sola
seleccion_tengo = st.pills(
    "Tengo", 
    list(range(start_active, end_active + 1)), 
    default=ids_tengo_live, 
    selection_mode="multi", 
    key=key_pills
)

st.markdown("### 2️⃣ ¿Cuáles REPETISTE?")
# Lógica cascada con lo que acabas de tocar
posibles_repetidas = sorted(seleccion_tengo) if seleccion_tengo else []
# Recuperar repetidas previas (limpiando las que ya no tengo)
ids_repetidas_validos = [k for k in repetidas_info.keys() if k in posibles_repetidas]

seleccion_repes = st.pills(
    "Repetidas", 
    posibles_repetidas, 
    default=ids_repetidas_validos, 
    selection_mode="multi", 
    key=f"pills_repes_{seleccion}"
)

# Editor de Precios
edited_df = pd.DataFrame()
if seleccion_repes:
    st.caption("💲 Precios")
    ed_data = []
    for num in seleccion_repes:
        info = repetidas_info.get(num, {'price': 0})
        modo = "Venta" if info['price'] > 0 else "Canje"
        ed_data.append({"Figurita": num, "Modo": modo, "Precio": info['price']})
    
    edited_df = st.data_editor(pd.DataFrame(ed_data), column_config={
        "Figurita": st.column_config.NumberColumn(disabled=True),
        "Modo": st.column_config.SelectboxColumn(options=["Canje", "Venta"], required=True),
        "Precio": st.column_config.NumberColumn(min_value=0, step=100)
    }, hide_index=True, use_container_width=True, key=f"editor_{seleccion}")

st.markdown("---")
if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
    save_inventory_inverted(user['id'], start_active, end_active, seleccion_tengo, edited_df)
    st.toast("¡Guardado!", icon="✅"); time.sleep(1); st.rerun()

st.divider()
st.subheader("🔍 Mercado")
# ... (El mercado sigue igual)
market_df = fetch_market(user['id'])
matches, ventas = find_matches(user['id'], market_df)

t1, t2 = st.tabs([f"Canjes ({len(matches)})", f"Ventas ({len(ventas)})"])
with t1:
    for m in matches:
        with st.container(border=True):
            st.markdown(f"🔄 **{m['nick']}** cambia **#{m['figu']}** por tu **#{m['te_pide']}**")
            if st.button("WhatsApp", key=f"c_{m['figu']}"):
                if check_contact_limit(user): consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{m['phone']})")
                else: st.error("Límite diario alcanzado.")
with t2:
    for v in ventas:
        with st.container(border=True):
            st.markdown(f"💰 **{v['nick']}** vende **#{v['figu']}** a **${v['price']}**")
            if st.button("WhatsApp", key=f"v_{v['figu']}"):
                if check_contact_limit(user): consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{v['phone']})")
                else: st.error("Límite diario alcanzado.")