import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago
import bcrypt
import re

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILO (VERDE) ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

st.markdown(
    """
    <style>
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
    div[data-testid="stPills"] span:hover, div[data-testid="stPills"] button:hover {
        border-color: #66bb6a !important;
        color: #2e7d32 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. CONEXIÓN A SUPABASE Y MERCADO PAGO ---
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
    st.error(f"Error de configuración (Secrets): {e}")
    st.stop()

# --- 3. DATOS DEL ÁLBUM ---
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

# --- 4. FUNCIONES DE SEGURIDAD ---
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

# --- 5. LÓGICA DE INVENTARIO (CON RED DE SEGURIDAD ANTI-CRASH) ---
def get_inventory_status(user_id, start, end):
    # Traemos lo que el usuario YA TIENE guardado en BD
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    # --- FIX CRÍTICO: Si la BD está vacía, crear columnas vacías ---
    if df.empty:
        df = pd.DataFrame(columns=['sticker_num', 'status', 'price', 'user_id'])
    # -----------------------------------------------------------------

    db_tengo = []
    db_repetidas_info = {}
    
    if not df.empty:
        # Filtramos solo el rango de la página actual
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        
        # Recuperamos las que tienen status 'tengo'
        db_tengo = df_page[df_page['status'] == 'tengo']['sticker_num'].tolist()
        
        # Recuperamos repetidas
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            db_repetidas_info[row['sticker_num']] = {'price': row['price']}
            # Si está como repetida, asumimos que también la tiene
            if row['sticker_num'] not in db_tengo:
                db_tengo.append(row['sticker_num'])
                
    return db_tengo, db_repetidas_info, df

def save_inventory_positive(user_id, start, end, ui_owned_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    
    # Borramos todo el rango para reescribirlo limpio
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    new_rows = []
    # 1. Guardar 'tengo'
    for num in ui_owned_list:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "tengo", "price": 0})
        
    # 2. Guardar 'repetida'
    if not ui_repe_df.empty:
        for _, row in ui_repe_df.iterrows():
            new_rows.append({
                "user_id": user_id, 
                "sticker_num": row['Figurita'], 
                "status": "repetida", 
                "price": int(row['Precio']) if row['Modo'] == "Venta" else 0
            })
            
    if new_rows: supabase.table("inventory").insert(new_rows).execute()

# --- 6. MERCADO ---
def fetch_market(user_id):
    resp = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", user_id).execute()
    return pd.DataFrame(resp.data)

def find_matches(user_id, market_df):
    # Lógica de Match adaptada: Busco lo que NO tengo
    
    # Mis figuritas
    resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "tengo").execute()
    mis_tengo_set = set(item['sticker_num'] for item in resp.data)
    
    # Mis repetidas (para trueque)
    resp_r = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "repetida").execute()
    mis_repes_set = set(item['sticker_num'] for item in resp_r.data)
    
    directos, ventas = [], []
    if market_df.empty: return [], []
    
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    
    # Buscamos ofertas de REPETIDAS de otros
    ofertas = market_df[market_df['status'] == 'repetida']
    
    for _, row in ofertas.iterrows():
        figu = row['sticker_num']
        
        # Si NO la tengo, me interesa
        if figu not in mis_tengo_set:
            match = {'nick': row['nick'], 'zone': row['zone'], 'phone': row['phone'], 'figu': figu, 'price': row['price']}
            
            if row['price'] > 0:
                ventas.append(match)
            else:
                # Trueque: ¿Tengo algo que él no tenga?
                # Sus 'tengo'
                sus_tengo_list = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'tengo')]['sticker_num'].tolist()
                sus_tengo_set = set(sus_tengo_list)
                
                # Cruce: Mis repetidas que él NO tiene
                sirven = [r for r in mis_repes_set if r not in sus_tengo_set]
                
                if sirven:
                    match['te_pide'] = sirven[0]
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

# --- 7. INTERFAZ DE USUARIO ---

# Inicializar sesión
if 'user' not in st.session_state: st.session_state.user = None

# PANTALLA DE LOGIN
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

# APP PRINCIPAL
user = st.session_state.user

# --- CÁLCULOS DINÁMICOS DE PROGRESO ---
seleccion_pais = st.session_state.get("seleccion_pais_key", list(ALBUM_PAGES.keys())[0])
start_active, end_active = ALBUM_PAGES[seleccion_pais]
total_active = end_active - start_active + 1
total_album = sum([(v[1] - v[0] + 1) for v in ALBUM_PAGES.values()])

# Datos de BD (AQUÍ ES DONDE ANTES FALLABA)
ids_tengo_db, repetidas_info, df_full = get_inventory_status(user['id'], start_active, end_active)

# Datos EN VIVO (Session State para reactividad)
key_pills = f"pills_tengo_{seleccion_pais}"
if key_pills in st.session_state:
    ids_tengo_live = st.session_state[key_pills]
else:
    ids_tengo_live = ids_tengo_db

tengo_live_count = len(ids_tengo_live) # De la sección activa

# Global = (Total BD - Lo viejo de esta sección) + Lo nuevo de esta sección
# (Usamos try/except por si el df está vacío)
try:
    tengo_db_total = df_full[df_full['status'] == 'tengo'].shape[0]
except:
    tengo_db_total = 0 # Si falla, es 0

tengo_db_esta_seccion = len(ids_tengo_db)
tengo_global_live = (tengo_db_total - tengo_db_esta_seccion) + tengo_live_count

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    if user['phone'] == ADMIN_PHONE: st.info("🕵️ ADMIN")
    
    st.divider()
    # BARRA GLOBAL
    progreso_global = min(tengo_global_live / total_album, 1.0)
    st.progress(progreso_global, text="Álbum Completo")
    st.caption(f"Tienes **{tengo_global_live}** de {total_album} figuritas.")
    st.divider()

    if user['is_premium']: st.success("💎 PREMIUM")
    else: 
        st.warning("👤 GRATIS")
        st.link_button("👉 Activar Premium", MP_LINK)
        if st.button("Validar Pago"):
            op = st.text_input("ID Op", key="op_v")
            if op and st.button("OK"):
                exito, msg = verificar_pago_mp(op, user['id'])
                if exito: st.success(msg); time.sleep(2); st.rerun()
    if st.button("Salir"): st.session_state.user = None; st.rerun()

# --- PÁGINA CENTRAL ---
st.header("📖 Mi Álbum")

seleccion = st.selectbox("Selecciona Sección:", list(ALBUM_PAGES.keys()), key="seleccion_pais_key")

# BARRA LOCAL
progreso_local = min(tengo_live_count / total_active, 1.0)
st.progress(progreso_local, text=f"Sección {seleccion}: Tienes {tengo_live_count} de {total_active}")

st.divider()

st.markdown("### 1️⃣ ¿Cuáles TENÉS? (Verde ✅)")
seleccion_tengo = st.pills("Tengo", list(range(start_active, end_active + 1)), default=ids_tengo_live, selection_mode="multi", key=key_pills)

st.markdown("### 2️⃣ ¿Cuáles REPETISTE?")
posibles_repetidas = sorted(seleccion_tengo) if seleccion_tengo else []
ids_repetidas_validos = [k for k in repetidas_info.keys() if k in posibles_repetidas]

seleccion_repes = st.pills("Repetidas", posibles_repetidas, default=ids_repetidas_validos, selection_mode="multi", key=f"pills_repes_{seleccion}")

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
    save_inventory_positive(user['id'], start_active, end_active, seleccion_tengo, edited_df)
    st.toast("¡Guardado!", icon="✅"); time.sleep(1); st.rerun()

st.divider()
st.subheader("🔍 Mercado")
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