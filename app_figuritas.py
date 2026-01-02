import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago
import bcrypt
import re

# --- CONFIGURACIÓN E INYECCIÓN DE ESTILO (VERDE) ---
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

# --- 🧠 LÓGICA DE DATOS CORREGIDA (POSITIVA) ---

def get_inventory_status(user_id, start, end):
    """
    Ahora traemos lo que TENEMOS (status='tengo').
    Si la BD está vacía, devuelve lista vacía. (Correcto: 0%)
    """
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    db_tengo = []
    db_repetidas_info = {}
    
    if not df.empty:
        # Filtro rango
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        
        # Lógica Positiva: Buscamos 'tengo' y 'repetida'
        # Nota: Asumimos que si tienes 'repetida', implícitamente la 'tienes'.
        # Pero para mantener limpio, el usuario debe marcar 'tengo' en la lista 1.
        
        db_tengo = df_page[df_page['status'] == 'tengo']['sticker_num'].tolist()
        
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            db_repetidas_info[row['sticker_num']] = {'price': row['price']}
            # Robustez: Si está repetida pero no en 'tengo' (error de datos), la agregamos visualmente
            if row['sticker_num'] not in db_tengo:
                db_tengo.append(row['sticker_num'])
                
    return db_tengo, db_repetidas_info, df

def save_inventory_positive(user_id, start, end, ui_owned_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    # Limpiamos todo el rango
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    new_rows = []
    # 1. Guardar 'tengo' (POSITIVO)
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

def fetch_market(user_id):
    # Traemos todo el mercado
    resp = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", user_id).execute()
    return pd.DataFrame(resp.data)

def find_matches(user_id, market_df):
    # Lógica de Match adaptada a 'tengo'
    # Mis Faltantes = Todo el álbum - Mis 'tengo'
    
    # 1. Obtener mis 'tengo'
    resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "tengo").execute()
    mis_tengo_set = set(item['sticker_num'] for item in resp.data)
    
    # 2. Obtener mis 'repetidas' para ofrecer trueque
    resp_r = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "repetida").execute()
    mis_repes_set = set(item['sticker_num'] for item in resp_r.data)
    
    directos, ventas = [], []
    if market_df.empty: return [], []
    
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    
    # Ofertas: Gente que tiene repetida una figurita que yo NO tengo
    # Filtro 1: Status repetida
    ofertas = market_df[market_df['status'] == 'repetida']
    
    for _, row in ofertas.iterrows():
        figu = row['sticker_num']
        
        # Filtro 2: ¿Yo la tengo?
        if figu not in mis_tengo_set:
            match = {'nick': row['nick'], 'zone': row['zone'], 'phone': row['phone'], 'figu': figu, 'price': row['price']}
            
            if row['price'] > 0:
                ventas.append(match)
            else:
                # Trueque: Él me da 'figu'. ¿Yo tengo algo que él NO tenga?
                # Sus 'tengo'
                sus_tengo_list = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'tengo')]['sticker_num'].tolist()
                sus_tengo_set = set(sus_tengo_list)
                
                # Cruce: Mis repetidas que él NO tiene
                sirven = [r for r in mis_repes_set if r not in sus_tengo_set]
                
                if sirven:
                    match['te_pide'] = sirven[0] # Le ofrezco la primera que sirva
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

# --- CÁLCULO DE PROGRESO DINÁMICO ---
# 1. Inicialización
seleccion_pais = st.session_state.get("seleccion_pais_key", list(ALBUM_PAGES.keys())[0])
start_active, end_active = ALBUM_PAGES[seleccion_pais]
total_active = end_active - start_active + 1
total_album = sum([(v[1] - v[0] + 1) for v in ALBUM_PAGES.values()])

# 2. Datos de BD
ids_tengo_db, repetidas_info, df_full = get_inventory_status(user['id'], start_active, end_active)

# 3. Datos EN VIVO (Session