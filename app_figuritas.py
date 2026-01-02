import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago
import bcrypt
import re

# --- 1. CONFIGURACIÓN E INYECCIÓN DE ESTILO ---
st.set_page_config(page_title="Figus 26 | Colección", layout="wide", page_icon="⚽")

st.markdown(
    """
    <style>
    /* Estilo Verde para selección */
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
    /* Botones redondeados */
    button[kind="secondary"] {
        border-radius: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. CONEXIÓN ---
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

# --- 3. TEXTO LEGAL COMPLETO ---
TERMINOS_TEXTO = """
TÉRMINOS Y CONDICIONES - FIGUS 26
1. EDAD: Debes ser mayor de 18 años.
2. RESPONSABILIDAD: Los encuentros presenciales son bajo tu exclusivo riesgo. Figus 26 no se hace responsable por seguridad, robos o conflictos.
3. PRIVACIDAD: Aceptas que tu teléfono sea visible para otros coleccionistas con el fin de intercambiar.
4. CONDUCTA: Se prohíbe el acoso, spam o venta de artículos ilegales.
5. PAGOS: Los pagos Premium no son reembolsables.
"""

# --- 4. POP-UP DE INICIO (BARRERA DE EDAD) ---
@st.dialog("⚠️ Bienvenido a Figus 26")
def mostrar_barrera_entrada():
    st.warning("🔞 Esta aplicación es para mayores de 18 años.")
    st.info("🤝 Facilitamos el contacto entre coleccionistas, pero no intervenimos en los canjes ni garantizamos seguridad en los encuentros.")
    
    st.markdown("**Al continuar, declaras que:**")
    st.markdown("* Eres mayor de edad.")
    st.markdown("* Asumes la responsabilidad de tus encuentros.")
    
    if st.button("✅ Entendido, soy +18", type="primary", use_container_width=True):
        st.session_state.barrera_superada = True
        st.rerun()

# --- 5. FUNCIONES DE SEGURIDAD Y VALIDACIÓN ---

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_text, hashed_text):
    try: return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_text.encode('utf-8'))
    except: return False

def limpiar_telefono(phone_input):
    if not phone_input: return ""
    return re.sub(r"\D", "", phone_input)

def validar_formato_telefono(phone_clean):
    return bool(re.match(r"^\d{10,14}$", phone_clean))

# --- FUNCIONES DE DB ---

def login_user(phone, password):
    clean_phone = limpiar_telefono(phone)
    if not clean_phone: return None, "Ingresa un teléfono."
    response = supabase.table("users").select("*").eq("phone", clean_phone).execute()
    if not response.data: return None, "Usuario no encontrado."
    user = response.data[0]
    if check_password(password, user['password']): return user, "OK"
    else: return None, "Contraseña incorrecta."

def register_user(nick, phone, zone, password):
    clean_phone = limpiar_telefono(phone)
    if not validar_formato_telefono(clean_phone):
        return None, "Teléfono inválido. Verifica código de área."
    if not nick or not password:
        return None, "Falta Nick o Contraseña."
    if supabase.table("users").select("*").eq("phone", clean_phone).execute().data:
        return None, "Teléfono ya registrado."
    try:
        hashed_pw = hash_password(password)
        data = {"nick": nick, "phone": clean_phone, "zone": zone, "password": hashed_pw, "is_admin": (clean_phone == ADMIN_PHONE), "reputation": 0}
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

# --- SISTEMA DE REPUTACIÓN ---
def votar_usuario(voter_id, target_id):
    if voter_id == target_id: return False, "No puedes votarte a ti mismo."
    check = supabase.table("votes").select("*").eq("voter_id", voter_id).eq("target_id", target_id).execute()
    if check.data: return False, "Ya has recomendado a este usuario."
    try:
        supabase.table("votes").insert({"voter_id": voter_id, "target_id": target_id}).execute()
        curr_rep = supabase.table("users").select("reputation").eq("id", target_id).execute().data[0]['reputation'] or 0
        supabase.table("users").update({"reputation": curr_rep + 1}).eq("id", target_id).execute()
        return True, "¡Recomendación enviada!"
    except Exception as e: return False, str(e)

# --- INVENTARIO ---
def get_inventory_status(user_id, start, end):
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    if df.empty: df = pd.DataFrame(columns=['sticker_num', 'status', 'price', 'user_id'])

    db_tengo = []
    db_repetidas_info = {}
    
    if not df.empty:
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        db_tengo = df_page[df_page['status'] == 'tengo']['sticker_num'].tolist()
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            db_repetidas_info[row['sticker_num']] = {'price': row['price']}
            if row['sticker_num'] not in db_tengo: db_tengo.append(row['sticker_num'])
                
    return db_tengo, db_repetidas_info, df

def save_inventory_positive(user_id, start, end, ui_owned_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    new_rows = []
    for num in ui_owned_list:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "tengo", "price": 0})
    if not ui_repe_df.empty: