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
        for _, row in ui_repe_df.iterrows():
            new_rows.append({
                "user_id": user_id, "sticker_num": row['Figurita'], 
                "status": "repetida", 
                "price": int(row['Precio']) if row['Modo'] == "Venta" else 0
            })
    if new_rows: supabase.table("inventory").insert(new_rows).execute()

# --- MERCADO ---
def fetch_market(user_id):
    resp = supabase.table("inventory").select("*, users(nick, zone, phone, reputation)").neq("user_id", user_id).execute()
    return pd.DataFrame(resp.data)

def find_matches(user_id, market_df):
    resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "tengo").execute()
    mis_tengo_set = set(item['sticker_num'] for item in resp.data)
    
    resp_r = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "repetida").execute()
    mis_repes_set = set(item['sticker_num'] for item in resp_r.data)
    
    directos, ventas = [], []
    if market_df.empty: return [], []
    
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    market_df['reputation'] = market_df['users'].apply(lambda x: x.get('reputation', 0))
    market_df['other_id'] = market_df['users'].apply(lambda x: x.get('id', 0))
    
    ofertas = market_df[market_df['status'] == 'repetida']
    
    for _, row in ofertas.iterrows():
        figu = row['sticker_num']
        if figu not in mis_tengo_set:
            match = {
                'nick': row['nick'], 'zone': row['zone'], 'phone': row['phone'], 
                'figu': figu, 'price': row['price'], 
                'reputation': row['reputation'], 'target_id': row['user_id']
            }
            if row['price'] > 0: ventas.append(match)
            else:
                sus_tengo_list = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'tengo')]['sticker_num'].tolist()
                sus_tengo_set = set(sus_tengo_list)
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

# --- 6. BLOQUEO INICIAL (BARRERA DE EDAD) ---
if 'barrera_superada' not in st.session_state:
    st.session_state.barrera_superada = False

if not st.session_state.barrera_superada:
    mostrar_barrera_entrada()

# --- 7. UI PRINCIPAL (LOGIN / REGISTRO) ---

if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏆 Figus 26")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    
    with t1: # LOGIN
        p = st.text_input("Teléfono (ej: 261 555 1234)")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar", type="primary"):
            u, m = login_user(p, pw)
            if u: st.session_state.user = u; st.rerun()
            else: st.error(m)
            
    with t2: # REGISTRO CON CHECKBOX LEGAL
        st.caption("Crea tu cuenta para guardar tu álbum.")
        
        n = st.text_input("Apodo / Nick")
        ph = st.text_input("Teléfono (Será tu ID)")
        st.caption("Ingresa tu número con código de área.")
        passw = st.text_input("Crea una Contraseña", type="password")
        z = st.selectbox("Tu Zona", ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"])
        
        st.divider()
        
        # --- NUEVO: Checkbox Obligatorio ---
        with st.expander("📄 Leer Términos y Condiciones"):
            st.markdown(TERMINOS_TEXTO)
            
        acepto_terminos = st.checkbox("He leído y acepto los Términos y Condiciones.")
        
        # El botón está deshabilitado (disabled=True) si NO aceptó términos
        if st.button("Crear Cuenta", disabled=not acepto_terminos):
            u, m = register_user(n, ph, z, passw)
            if u: st.success("¡Cuenta creada!"); st.balloons()
            else: st.error(m)
        
        if not acepto_terminos:
            st.caption("Debes aceptar los términos para habilitar el botón.")
            
    st.stop()

# --- APP LOGUEADA ---
user = st.session_state.user

# Cálculos
seleccion_pais = st.session_state.get("seleccion_pais_key", list(ALBUM_PAGES.keys())[0])
start_active, end_active = ALBUM_PAGES[seleccion_pais]
total_active = end_active - start_active + 1
total_album = sum([(v[1] - v[0] + 1) for v in ALBUM_PAGES.values()])

ids_tengo_db, repetidas_info, df_full = get_inventory_status(user['id'], start_active, end_active)
key_pills = f"pills_tengo_{seleccion_pais}"
if key_pills in st.session_state: ids_tengo_live = st.session_state[key_pills]
else: ids_tengo_live = ids_tengo_db

tengo_live_count = len(ids_tengo_live)
try: tengo_db_total = df_full[df_full['status'] == 'tengo'].shape[0]
except: tengo_db_total = 0
tengo_db_esta_seccion = len(ids_tengo_db)
tengo_global_live = (tengo_db_total - tengo_db_esta_seccion) + tengo_live_count

# SIDEBAR
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    my_rep = user.get('reputation', 0)
    st.caption(f"⭐ Tu Reputación: {my_rep} votos")
    
    if user['phone'] == ADMIN_PHONE: st.info("🕵️ ADMIN")
    st.divider()
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
    
    # Link a términos en sidebar también
    with st.expander("Ayuda & Legales"):
        st.caption(TERMINOS_TEXTO)

# CONTENIDO
st.header("📖 Mi Álbum")
seleccion = st.selectbox("Selecciona Sección:", list(ALBUM_PAGES.keys()), key="seleccion_pais_key")
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
    if not matches: st.info("No hay canjes directos disponibles.")
    for m in matches:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"🔄 **{m['nick']}** (⭐{m['reputation']}) cambia **#{m['figu']}** por tu **#{m['te_pide']}**")
                st.caption(f"Zona: {m['zone']}")
            with c2:
                if st.button("WhatsApp", key=f"c_{m['figu']}_{m['target_id']}"):
                    if check_contact_limit(user): consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{m['phone']})")
                    else: st.error("Límite diario.")
            with c3:
                if st.button("👍 Recomendar", key=f"vote_{m['figu']}_{m['target_id']}"):
                    ok, msg = votar_usuario(user['id'], m['target_id'])
                    if ok: st.toast(msg, icon="⭐")
                    else: st.toast(msg, icon="🚫")

with t2:
    if not ventas: st.info("Nadie vende lo que buscas.")
    for v in ventas:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"💰 **{v['nick']}** (⭐{v['reputation']}) vende **#{v['figu']}** a **${v['price']}**")
            with c2:
                if st.button("WhatsApp", key=f"v_{v['figu']}_{v['target_id']}"):
                    if check_contact_limit(user): consume_credit(user); st.markdown(f"[Chat](https://wa.me/549{v['phone']})")
                    else: st.error("Límite diario.")
            with c3:
                if st.button("👍 Recomendar", key=f"vote_v_{v['figu']}_{v['target_id']}"):
                    ok, msg = votar_usuario(user['id'], v['target_id'])
                    if ok: st.toast(msg, icon="⭐")
                    else: st.toast(msg, icon="🚫")