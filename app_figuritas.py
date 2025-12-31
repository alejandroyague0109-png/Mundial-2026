import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago # Nueva librería

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Figus 26 | Pro", layout="wide", page_icon="⚽")

# --- 🛠️ TUS DATOS ---
ADMIN_PHONE = "2611234567"  # <--- TU NÚMERO
# PRECIO DEL PREMIUM (Debe coincidir con lo que cobras en MP)
PRECIO_PREMIUM = 5000 
MP_LINK = "https://link.mercadopago.com.ar/..." # <--- TU LINK

# Conexiones
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    mp_token = st.secrets["MP_ACCESS_TOKEN"]
    
    supabase: Client = create_client(url, key)
    sdk = mercadopago.SDK(mp_token) # Inicializamos MP
except:
    st.error("Error de configuración: Faltan Secrets (Supabase o MP).")
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

# --- FUNCIONES ---

def login_user(phone, password):
    response = supabase.table("users").select("*").eq("phone", phone).execute()
    if not response.data: return None, "Usuario no encontrado."
    user = response.data[0]
    if user['password'] == password: return user, "OK"
    else: return None, "Contraseña incorrecta."

def register_user(nick, phone, zone, password):
    if supabase.table("users").select("*").eq("phone", phone).execute().data:
        return None, "El teléfono ya existe."
    try:
        data = {"nick": nick, "phone": phone, "zone": zone, "password": password, "is_admin": (phone == ADMIN_PHONE)}
        response = supabase.table("users").insert(data).execute()
        return response.data[0], "OK"
    except Exception as e: return None, str(e)

def verificar_pago_mp(payment_id, user_id):
    """Consulta a la API de Mercado Pago si el pago es real"""
    try:
        # 1. Verificar si ya se usó este ID en nuestra base de datos
        ya_usado = supabase.table("payments_log").select("*").eq("payment_id", payment_id).execute()
        if ya_usado.data:
            return False, "Este comprobante ya fue utilizado."

        # 2. Preguntar a Mercado Pago
        payment_info = sdk.payment().get(payment_id)
        
        if payment_info["status"] == 404:
            return False, "ID de pago no encontrado."
        
        response = payment_info["response"]
        
        # 3. Validar condiciones
        status = response.get("status")
        amount = response.get("transaction_amount")
        
        if status == "approved" and amount >= PRECIO_PREMIUM:
            # 4. Registrar el uso para que no se repita
            supabase.table("payments_log").insert({
                "payment_id": str(payment_id),
                "user_id": user_id,
                "amount": amount,
                "status": status
            }).execute()
            
            # 5. Activar Premium
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Pago validado! Eres Premium."
        else:
            return False, f"El pago no está aprobado o el monto es menor a ${PRECIO_PREMIUM}."
            
    except Exception as e:
        return False, f"Error validando: {str(e)}"

# [MANTENER AQUÍ RESTO DE FUNCIONES: get_inventory_details, save_album_page_advanced, fetch_all_market_data, find_matches, check_contact_limit, consume_contact_credit]
# (Copia las funciones del código anterior para mantener la respuesta limpia, son las mismas)
def get_inventory_details(user_id, start, end):
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    faltantes_ids = []
    repetidas_data = {}
    if not df.empty:
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        faltantes_ids = df_page[df_page['status'] == 'faltante']['sticker_num'].tolist()
        repes_rows = df_page[df_page['status'] == 'repetida']
        for _, row in repes_rows.iterrows():
            repetidas_data[row['sticker_num']] = {'price': row['price']}
    return faltantes_ids, repetidas_data

def save_album_page_advanced(user_id, start, end, selected_faltas, df_repetidas_config):
    page_numbers = list(range(start, end + 1))
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    new_rows = []
    for num in selected_faltas:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "faltante", "price": 0})
    if not df_repetidas_config.empty:
        for _, row in df_repetidas_config.iterrows():
            num = row['Figurita']
            modo = row['Modo']
            precio = row['Precio'] if modo == "Venta" else 0
            new_rows.append({"user_id": user_id, "sticker_num": num, "status": "repetida", "price": int(precio)})
    if new_rows:
        supabase.table("inventory").insert(new_rows).execute()

def fetch_all_market_data(mi_id):
    response = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", mi_id).execute()
    return pd.DataFrame(response.data)

def find_matches(user_id, market_df):
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    mi_df = pd.DataFrame(response.data)
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
        if row['price'] > 0:
            ventas.append(match)
        else:
            sus_faltas = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'faltante')]['sticker_num'].tolist()
            cruce = set(mis_r).intersection(set(sus_faltas))
            if cruce:
                match['te_pide'] = list(cruce)[0]
                directos.append(match)
    return directos, ventas

def check_contact_limit(user):
    if user['is_premium']: return True
    hoy = str(date.today())
    if str(user['last_contact_date']) != hoy:
        supabase.table("users").update({"last_contact_date": hoy, "daily_contacts_count": 0}).eq("id", user['id']).execute()
        return True
    return user['daily_contacts_count'] < 1

def consume_contact_credit(user):
    if not user['is_premium']:
        nuevo = user['daily_contacts_count'] + 1
        supabase.table("users").update({"daily_contacts_count": nuevo}).eq("id", user['id']).execute()
        st.session_state.user['daily_contacts_count'] = nuevo

# --- INTERFAZ ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    st.title("🏆 Figus 26")
    tab_log, tab_reg = st.tabs(["Ingresar", "Registrarse"])
    with tab_log:
        p = st.text_input("Teléfono")
        pw = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            u, m = login_user(p, pw)
            if u: 
                st.session_state.user = u
                st.rerun()
            else: st.error(m)
    with tab_reg:
        n = st.text_input("Nick")
        ph = st.text_input("Teléfono (ID)")
        passw = st.text_input("Crear Contraseña", type="password")
        z = st.selectbox("Zona", ["Centro", "Godoy Cruz", "Guaymallén", "Las Heras"])
        if st.button("Crear Cuenta"):
            u, m = register_user(n, ph, z, passw)
            if u: st.success("Creado! Ingresa ahora.")
            else: st.error(m)
    st.stop()

user = st.session_state.user

with st.sidebar:
    st.title(f"Hola {user['nick']}")
    
    if user['is_premium']: 
        st.success("💎 PREMIUM ACTIVADO")
    else: 
        st.info("👤 CUENTA GRATIS")
        st.progress(user['daily_contacts_count']/1, f"Contactos: {user['daily_contacts_count']}/1")
        
        st.divider()
        st.markdown("### 🚀 Activar Premium")
        st.markdown("1. Paga $5000 con Mercado Pago.")
        st.link_button("👉 Pagar Ahora", MP_LINK)
        st.markdown("2. Al terminar, copia el **Número de Operación** del comprobante y pégalo aquí:")
        
        op_id = st.text_input("Nro. Operación (ej: 1234567890)")
        if st.button("✅ Validar Pago"):
            if not op_id:
                st.warning("Pega el número primero.")
            else:
                exito, msg = verificar_pago_mp(op_id, user['id'])
                if exito:
                    st.balloons()
                    st.success(msg)
                    time.sleep(3)
                    st.session_state.user['is_premium'] = True
                    st.rerun()
                else:
                    st.error(msg)

    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum Pro")

paises = list(ALBUM_PAGES.keys())
seleccion = st.selectbox("Selecciona Sección:", paises)

start, end = ALBUM_PAGES[seleccion]
numeros_posibles = list(range(start, end + 1))
mis_f_ids, repetidas_info_dict = get_inventory_details(user['id'], start, end)

with st.form("album_advanced"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🔴 Faltantes")
        nuevas_faltas = st.pills("Busco:", numeros_posibles, default=mis_f_ids, selection_mode="multi", key="pf")
    with col2:
        st.markdown("### 🟢 Repetidas")
        mis_r_ids_actuales = list(repetidas_info_dict.keys())
        seleccion_repes = st.pills("Tengo:", numeros_posibles, default=mis_r_ids_actuales, selection_mode="multi", key="pr")
        
    if seleccion_repes:
        st.markdown("#### 💲 Configurar Precios")
        editor_data = []
        for num in seleccion_repes:
            info = repetidas_info_dict.get(num, {'price': 0})
            modo = "Venta" if info['price'] > 0 else "Canje"
            editor_data.append({"Figurita": num, "Modo": modo, "Precio": info['price']})
        df_editor = pd.DataFrame(editor_data)
        edited_df = st.data_editor(df_editor, column_config={
            "Figurita": st.column_config.NumberColumn(disabled=True),
            "Modo": st.column_config.SelectboxColumn(options=["Canje", "Venta"], required=True),
            "Precio": st.column_config.NumberColumn(min_value=0, step=100)
        }, hide_index=True, use_container_width=True)
    else:
        edited_df = pd.DataFrame()
        
    guardar = st.form_submit_button("💾 Guardar Todo", use_container_width=True)

if guardar:
    if set(nuevas_faltas).intersection(set(seleccion_repes)):
        st.error("Error: Una figurita no puede ser Faltante y Repetida a la vez.")
    else:
        save_album_page_advanced(user['id'], start, end, nuevas_faltas, edited_df)
        st.toast(f"¡{seleccion} guardado!", icon="✅")
        time.sleep(1)
        st.rerun()

st.divider()
st.subheader("🔍 Mercado")
market_df = fetch_all_market_data(user['id'])
matches, ventas = find_matches(user['id'], market_df)

t1, t2 = st.tabs([f"Canjes ({len(matches)})", f"Ventas ({len(ventas)})"])
with t1:
    for m in matches:
        with st.container(border=True):
            st.markdown(f"🔄 **{m['nick']}** cambia **#{m['figu']}** por tu **#{m['te_pide']}**")
            if st.button("WhatsApp", key=f"wc_{m['figu']}_{m['phone']}"):
                if check_contact_limit(user):
                    consume_contact_credit(user)
                    st.markdown(f"[Chat](https://wa.me/549{m['phone']})")
                else: st.error("Límite diario alcanzado.")
with t2:
    for v in ventas:
        with st.container(border=True):
            st.markdown(f"💰 **{v['nick']}** vende **#{v['figu']}** a **${v['price']}**")
            if st.button("WhatsApp", key=f"wv_{v['figu']}_{v['phone']}"):
                if check_contact_limit(user):
                    consume_contact_credit(user)
                    st.markdown(f"[Chat](https://wa.me/549{v['phone']})")
                else: st.error("Límite diario alcanzado.")