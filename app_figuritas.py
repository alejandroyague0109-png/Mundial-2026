import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Figus 26 | Álbum Virtual", layout="wide", page_icon="⚽")

# --- 🛠️ TUS DATOS DE ADMINISTRADOR ---
ADMIN_PHONE = "2611234567"  # <--- TU NÚMERO
MP_LINK = "https://link.mercadopago.com.ar/..." # <--- TU LINK

# Conexión a Supabase
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Error de conexión: Revisa tus 'Secrets' en Streamlit Cloud.")
    st.stop()

# --- DATOS DEL ÁLBUM (CONFIGURACIÓN DE PÁGINAS) ---
# Aquí definimos qué números corresponden a cada país.
# He puesto un ejemplo. ¡Tú deberás completar los rangos reales cuando salga el álbum!
ALBUM_PAGES = {
    "FW - Intro / Museos": (1, 19),
    "ARG - Argentina": (20, 39),
    "BRA - Brasil": (40, 59),
    "FRA - Francia": (60, 79),
    "USA - Estados Unidos": (80, 99),
    "MEX - México": (100, 119),
    "CAN - Canadá": (120, 139),
    "ESP - España": (140, 159),
    # ... Puedes agregar más países aquí siguiendo el formato "Nombre": (Inicio, Fin)
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

def get_inventory_range(user_id, start, end):
    """Trae solo las figuritas de un rango específico (País)"""
    # Traemos todo el inventario del usuario (es más rápido filtrar en Python que hacer muchas llamadas)
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    faltantes_set = set()
    repetidas_set = set()
    
    if not df.empty:
        # Filtramos por el rango del país seleccionado
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        
        faltantes_set = set(df_page[df_page['status'] == 'faltante']['sticker_num'].tolist())
        repetidas_set = set(df_page[df_page['status'] == 'repetida']['sticker_num'].tolist())
        
    return faltantes_set, repetidas_set

def save_album_page(user_id, start, end, selected_faltas, selected_repes):
    """Guarda los cambios masivos de una página"""
    # 1. Borrar todo lo anterior de este rango para este usuario (Limpieza)
    #    Esto es necesario por si desmarcó una figurita.
    #    Nota: En SQL puro sería un DELETE WHERE num BETWEEN start AND end.
    #    Con Supabase-py es un poco más artesanal:
    
    # Obtenemos lista de todos los números posibles en esta página
    page_numbers = list(range(start, end + 1))
    
    # Borramos los existentes en este rango (para sobrescribir con lo nuevo)
    # Usamos filter 'in' (sticker_num está en la lista de la página)
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    # 2. Insertar las nuevas selecciones
    new_rows = []
    
    # Faltantes
    for num in selected_faltas:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "faltante", "price": 0})
        
    # Repetidas
    for num in selected_repes:
        # Por defecto precio 0 (Canje). Si quiere vender, que lo edite en detalles.
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "repetida", "price": 0})
        
    if new_rows:
        supabase.table("inventory").insert(new_rows).execute()

def fetch_all_market_data(mi_id):
    response = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", mi_id).execute()
    return pd.DataFrame(response.data)

def find_matches(mis_faltas_ids, mis_repes_ids, market_df):
    directos, ventas = [], []
    if market_df.empty: return [], []
    
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    
    # Buscamos quién tiene mis faltantes como repetidas
    ofertas = market_df[(market_df['status'] == 'repetida') & (market_df['sticker_num'].isin(mis_faltas_ids))]
    
    for _, row in ofertas.iterrows():
        match = {'nick': row['nick'], 'zone': row['zone'], 'phone': row['phone'], 'figu': row['sticker_num'], 'price': row['price']}
        if row['price'] > 0:
            ventas.append(match)
        else:
            # Trueque: Verificar si yo tengo algo que él busca
            sus_faltas = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'faltante')]['sticker_num'].tolist()
            cruce = set(mis_repes_ids).intersection(set(sus_faltas))
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

def get_full_inventory_ids(user_id):
    """Obtiene TODOS los IDs para el motor de búsqueda global"""
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    if df.empty: return [], []
    f = df[df['status'] == 'faltante']['sticker_num'].tolist()
    r = df[df['status'] == 'repetida']['sticker_num'].tolist()
    return f, r

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

# --- BARRA LATERAL (DATOS Y PREMIUM) ---
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

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum Virtual")

# SELECTOR DE PAÍS
paises = list(ALBUM_PAGES.keys())
seleccion = st.selectbox("Selecciona un País / Sección:", paises)

start, end = ALBUM_PAGES[seleccion]
numeros_posibles = list(range(start, end + 1))

# Cargar lo que el usuario YA tiene marcado en este país
mis_f_ids, mis_r_ids = get_inventory_range(user['id'], start, end)

st.info(f"Mostrando figuritas del **{start}** al **{end}**")

with st.form("album_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔴 Faltantes")
        st.caption("Selecciona las que buscas:")
        # Widget visual de selección múltiple (Chips)
        nuevas_faltas = st.pills(
            "Faltantes",
            options=numeros_posibles,
            default=list(mis_f_ids),
            selection_mode="multi",
            key="pills_faltas"
        )

    with col2:
        st.markdown("### 🟢 Repetidas")
        st.caption("Selecciona las que tienes para cambiar:")
        nuevas_repes = st.pills(
            "Repetidas",
            options=numeros_posibles,
            default=list(mis_r_ids),
            selection_mode="multi",
            key="pills_repes"
        )
        
    guardar = st.form_submit_button("💾 Guardar Cambios en este País", use_container_width=True)

if guardar:
    # Validar que no haya marcado la misma como falta y repe
    interseccion = set(nuevas_faltas).intersection(set(nuevas_repes))
    if interseccion:
        st.error(f"Error: No puedes tener la figurita {list(interseccion)} como Faltante y Repetida a la vez.")
    else:
        save_album_page(user['id'], start, end, nuevas_faltas, nuevas_repes)
        st.toast(f"¡{seleccion} actualizado!", icon="✅")
        time.sleep(1) # Esperar un poco para que Supabase procese
        st.rerun()

st.divider()

# --- SECCIÓN DE MATCHES (BUSCADOR) ---
st.subheader("🔍 Buscador de Canjes")

# Traer inventario completo para buscar matches (no solo la página actual)
full_f, full_r = get_full_inventory_ids(user['id'])
market_df = fetch_all_market_data(user['id'])
matches, ventas = find_matches(full_f, full_r, market_df)

tab1, tab2 = st.tabs([f"Canjes ({len(matches)})", f"Ventas ({len(ventas)})"])

with tab1:
    if not matches: st.caption("No hay coincidencias directas.")
    for m in matches:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"🔄 **{m['nick']}** ({m['zone']}) cambia **#{m['figu']}** por tu **#{m['te_pide']}**")
            if c2.button("WhatsApp", key=f"btn_c_{m['figu']}_{m['phone']}"):
                if check_contact_limit(user):
                    consume_contact_credit(user)
                    st.markdown(f"[Abrir Chat](https://wa.me/549{m['phone']})")
                else: st.error("Límite diario alcanzado.")

with tab2:
    if not ventas: st.caption("Nadie vende lo que buscas.")
    for v in ventas:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"💰 **{v['nick']}** vende **#{v['figu']}** a **${v['price']}**")
            if c2.button("Contactar", key=f"btn_v_{v['figu']}_{v['phone']}"):
                if check_contact_limit(user):
                    consume_contact_credit(user)
                    st.markdown(f"[Abrir Chat](https://wa.me/549{v['phone']})")
                else: st.error("Límite diario alcanzado.")