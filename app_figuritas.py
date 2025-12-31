import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Figus 26 | Álbum Pro", layout="wide", page_icon="⚽")

# --- 🛠️ TUS DATOS DE ADMINISTRADOR ---
ADMIN_PHONE = "2611234567"  # <--- TU NÚMERO
MP_LINK = "https://link.mercadopago.com.ar/..." # <--- TU LINK

# Conexión a Supabase
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error de conexión: Revisa tus 'Secrets'.")
    st.stop()

# --- DATOS DEL ÁLBUM ---
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

# --- FUNCIONES DE BASE DE DATOS ---

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

def get_inventory_details(user_id, start, end):
    """
    Trae los detalles completos (Estado + Precio) para cargar el editor.
    """
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    # Datos por defecto vacíos
    faltantes_ids = []
    repetidas_data = {} # Diccionario {num: {'price': 0, 'status': 'repetida'}}
    
    if not df.empty:
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        
        faltantes_ids = df_page[df_page['status'] == 'faltante']['sticker_num'].tolist()
        
        # Guardamos la info de precios de las repetidas existentes
        repes_rows = df_page[df_page['status'] == 'repetida']
        for _, row in repes_rows.iterrows():
            repetidas_data[row['sticker_num']] = {'price': row['price']}
            
    return faltantes_ids, repetidas_data

def save_album_page_advanced(user_id, start, end, selected_faltas, df_repetidas_config):
    """
    Guarda faltantes y la configuración detallada de precios.
    """
    # 1. Limpieza del rango (Borrar previo)
    page_numbers = list(range(start, end + 1))
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    new_rows = []
    
    # 2. Guardar Faltantes (Simple)
    for num in selected_faltas:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "faltante", "price": 0})
        
    # 3. Guardar Repetidas (Con datos del Editor)
    # df_repetidas_config viene del st.data_editor
    if not df_repetidas_config.empty:
        for _, row in df_repetidas_config.iterrows():
            num = row['Figurita']
            modo = row['Modo']
            precio = row['Precio'] if modo == "Venta" else 0 # Si es canje, forzamos 0
            
            new_rows.append({"user_id": user_id, "sticker_num": num, "status": "repetida", "price": int(precio)})
            
    if new_rows:
        supabase.table("inventory").insert(new_rows).execute()

def fetch_all_market_data(mi_id):
    response = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", mi_id).execute()
    return pd.DataFrame(response.data)

def find_matches(user_id, market_df):
    # Traer TODO mi inventario para cruzar
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

# --- INTERFAZ DE USUARIO ---

if 'user' not in st.session_state: st.session_state.user = None

# 1. LOGIN
if not st.session_state.user:
    st.title("🏆 Figus 26 | Mendoza")
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

# 2. APP PRINCIPAL
user = st.session_state.user

# --- SIDEBAR ---
with st.sidebar:
    st.title(f"Hola {user['nick']}")
    if user['is_premium']: st.success("💎 PREMIUM")
    else: 
        st.info("👤 GRATIS")
        st.progress(user['daily_contacts_count']/1, f"Contactos: {user['daily_contacts_count']}/1")
        st.link_button("👉 Hacerse Premium", MP_LINK)
    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

# --- PÁGINA ÁLBUM ---
st.header("📖 Mi Álbum - Gestión Avanzada")

paises = list(ALBUM_PAGES.keys())
seleccion = st.selectbox("Selecciona Sección:", paises)

start, end = ALBUM_PAGES[seleccion]
numeros_posibles = list(range(start, end + 1))

# Cargar datos existentes (IDs + Precios)
mis_f_ids, repetidas_info_dict = get_inventory_details(user['id'], start, end)

with st.form("album_advanced"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔴 Faltantes")
        nuevas_faltas = st.pills("Busco:", numeros_posibles, default=mis_f_ids, selection_mode="multi", key="pf")

    with col2:
        st.markdown("### 🟢 Repetidas (Selección)")
        # 1. Seleccionar QUÉ tengo
        mis_r_ids_actuales = list(repetidas_info_dict.keys())
        seleccion_repes = st.pills("Tengo:", numeros_posibles, default=mis_r_ids_actuales, selection_mode="multi", key="pr")
        
    st.markdown("---")
    
    # --- ZONA DE CONFIGURACIÓN DE PRECIOS ---
    # Convertimos la selección de 'pills' en una tabla editable
    if seleccion_repes:
        st.markdown("#### 💲 Configurar Repetidas (Precios)")
        st.caption("Define si las cambias o las vendes.")
        
        # Preparamos los datos para el editor
        editor_data = []
        for num in seleccion_repes:
            # Si ya existía, traemos su precio/modo. Si es nuevo, default Canje/$0
            info = repetidas_info_dict.get(num, {'price': 0})
            modo = "Venta" if info['price'] > 0 else "Canje"
            precio = info['price']
            
            editor_data.append({"Figurita": num, "Modo": modo, "Precio": precio})
            
        df_editor = pd.DataFrame(editor_data)
        
        # Mostramos la tabla editable
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "Figurita": st.column_config.NumberColumn(disabled=True),
                "Modo": st.column_config.SelectboxColumn(options=["Canje", "Venta"], required=True),
                "Precio": st.column_config.NumberColumn(min_value=0, step=100, format="$%d")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        edited_df = pd.DataFrame()
        
    guardar = st.form_submit_button("💾 Guardar Todo", use_container_width=True)

if guardar:
    # Validación simple
    if set(nuevas_faltas).intersection(set(seleccion_repes)):
        st.error("Error: Una figurita no puede ser Faltante y Repetida a la vez.")
    else:
        save_album_page_advanced(user['id'], start, end, nuevas_faltas, edited_df)
        st.toast(f"¡{seleccion} guardado correctamente!", icon="✅")
        time.sleep(1)
        st.rerun()

st.divider()

# --- BUSCADOR ---
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