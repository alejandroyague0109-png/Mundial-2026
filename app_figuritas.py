import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import time
import mercadopago
import bcrypt
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Figus 26 | Mi Colección", layout="wide", page_icon="⚽")

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

# --- FUNCIONES DE SEGURIDAD Y UTILIDADES ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_text, hashed_text):
    try: return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_text.encode('utf-8'))
    except: return False

def validar_telefono(phone):
    patron = re.compile(r"^\d{10,13}$")
    return bool(patron.match(phone))

# --- FUNCIONES DE BASE DE DATOS ---
def login_user(phone, password):
    response = supabase.table("users").select("*").eq("phone", phone).execute()
    if not response.data: return None, "Usuario no encontrado."
    user = response.data[0]
    if check_password(password, user['password']): return user, "OK"
    else: return None, "Contraseña incorrecta."

def register_user(nick, phone, zone, password):
    if not validar_telefono(phone): return None, "Teléfono inválido (solo números)."
    if supabase.table("users").select("*").eq("phone", phone).execute().data:
        return None, "El teléfono ya existe."
    try:
        hashed_pw = hash_password(password)
        data = {"nick": nick, "phone": phone, "zone": zone, "password": hashed_pw, "is_admin": (phone == ADMIN_PHONE)}
        response = supabase.table("users").insert(data).execute()
        return response.data[0], "OK"
    except Exception as e: return None, str(e)

def verificar_pago_mp(payment_id, user_id):
    try:
        ya_usado = supabase.table("payments_log").select("*").eq("payment_id", payment_id).execute()
        if ya_usado.data: return False, "Comprobante ya usado."
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 404: return False, "ID no encontrado."
        resp = payment_info["response"]
        if resp.get("status") == "approved" and resp.get("transaction_amount") >= PRECIO_PREMIUM:
            supabase.table("payments_log").insert({
                "payment_id": str(payment_id), "user_id": user_id, "amount": resp.get("transaction_amount"), "status": "approved"
            }).execute()
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Premium Activado!"
        else: return False, "Pago no aprobado o monto insuficiente."
    except Exception as e: return False, f"Error: {str(e)}"

# --- LÓGICA DE PROGRESO ---
def calcular_progreso_global(user_id):
    total_album = 0
    for key, val in ALBUM_PAGES.items():
        total_album += (val[1] - val[0] + 1)
    resp = supabase.table("inventory").select("sticker_num", count="exact").eq("user_id", user_id).eq("status", "faltante").execute()
    total_faltantes = resp.count if resp.count else 0
    return total_faltantes, total_album

# --- NUEVA LÓGICA DE INVENTARIO (INVERTIDA) ---
def get_inventory_status(user_id, start, end):
    """
    Recupera el estado pero lo invierte para la UI.
    Si NO está en la tabla como 'faltante', asume que la TIENE.
    """
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    
    numeros_rango = list(range(start, end + 1))
    
    # 1. Identificar Faltantes Reales (están en BD como 'faltante')
    db_faltantes = []
    db_repetidas_info = {}
    
    if not df.empty:
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        db_faltantes = df_page[df_page['status'] == 'faltante']['sticker_num'].tolist()
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            db_repetidas_info[row['sticker_num']] = {'price': row['price']}
    
    # 2. Calcular "Las que TENGO" (Todas - Faltantes)
    # Si el usuario es nuevo y no tiene filas, asumimos que le faltan todas (todavía no marcamos 'faltante' en BD, pero la UI las mostrará desmarcadas)
    # Lógica: UI_Owned = All - DB_Missing
    
    # PERO, si es la primera vez (no hay registros de faltantes), ¿cómo diferenciamos "Usuario nuevo" de "Usuario que tiene todo"?
    # Estrategia Robustez: Si hay 0 registros en BD para este usuario en este rango, asumimos que no tiene nada.
    
    ids_que_tengo = [n for n in numeros_rango if n not in db_faltantes]
    
    # Caso borde: Si el usuario es nuevo, db_faltantes está vacío, entonces parecería que tiene TODAS. 
    # Corrección: Necesitamos saber si existen registros.
    # Simplificación para MVP:
    # Usamos la lógica explícita: Guardamos Faltantes en BD. 
    # Al principio, cargamos "faltantes" masivamente o asumimos vacío?
    # MEJOR: La base de datos guarda explicitamente las FALTANTES.
    # Si borro la faltante -> La tengo.
    
    # PARA QUE FUNCIONE AL INICIO: El usuario deberá marcar lo que tiene.
    # El sistema asume que lo que NO está marcado como "Faltante" en la BD es porque LO TIENE.
    # PROBLEMA: Un usuario nuevo no tiene filas de "Faltante". El sistema pensaría que tiene el álbum lleno.
    
    # SOLUCIÓN DEL MVP:
    # Vamos a confiar en la UI.
    #ids_que_tengo = [n for n in numeros_rango if n not in db_faltantes] 
    
    # *FIX*: Si la query está vacía, ¿tiene todo o nada?
    # Para evitar confusión, vamos a usar una lógica de "Posesión Explícita" en la UI,
    # pero guardamos "Faltantes" en la BD para el motor de búsqueda.
    
    # Vamos a hacer una consulta para ver si hay ALGO registrado en este rango.
    # Si no hay NADA, asumimos que le falta todo (para pintar gris la UI).
    has_data = not df[ (df['sticker_num'] >= start) & (df['sticker_num'] <= end) ].empty
    
    if not has_data:
        ids_que_tengo = [] # No tiene nada
        # Y en el 'save' guardaremos todas como faltantes implícitamente
    else:
        ids_que_tengo = [n for n in numeros_rango if n not in db_faltantes]

    return ids_que_tengo, db_repetidas_info

def save_inventory_inverted(user_id, start, end, ui_owned_list, ui_repe_df):
    """
    Recibe lo que el usuario TIENE y REPITIO.
    Calcula lo que FALTA y guarda eso en la BD.
    """
    page_numbers = list(range(start, end + 1))
    
    # 1. Limpiar rango
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    
    new_rows = []
    
    # 2. Calcular Faltantes (Lo que NO marcó como Tengo)
    # Faltantes = Todo el rango - Lo que marcó que tiene
    ids_faltantes = [n for n in page_numbers if n not in ui_owned_list]
    
    for num in ids_faltantes:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "faltante", "price": 0})
        
    # 3. Guardar Repetidas (Las que marcó en la segunda lista)
    if not ui_repe_df.empty:
        for _, row in ui_repe_df.iterrows():
            num = row['Figurita']
            modo = row['Modo']
            precio = row['Precio'] if modo == "Venta" else 0
            new_rows.append({"user_id": user_id, "sticker_num": num, "status": "repetida", "price": int(precio)})
            
    # 4. Insertar lote
    if new_rows:
        supabase.table("inventory").insert(new_rows).execute()

# [FUNCIONES FETCH MARKET, MATCH, ETC SE MANTIENEN IGUALES]
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
        if row['price'] > 0: ventas.append(match)
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
            if u: st.session_state.user = u; st.rerun()
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
    if user['phone'] == ADMIN_PHONE: st.info("🕵️ ADMIN")
    
    # Progreso Global
    st.divider()
    cant_faltas, total_album = calcular_progreso_global(user['id'])
    
    # Ajuste visual: Si no hay datos (usuario nuevo), cant_faltas será 0 pero porque no cargó nada.
    # Corrección visual simple:
    percent_missing = min(cant_faltas / total_album, 1.0) if total_album > 0 else 1.0
    st.progress(percent_missing, text="Tu Álbum (Faltantes)")
    st.caption(f"Te faltan {cant_faltas} de {total_album}")
    st.divider()

    if user['is_premium']: st.success("💎 PREMIUM")
    else: 
        st.warning("👤 GRATIS")
        st.link_button("👉 Activar Premium", MP_LINK)
        op_id = st.text_input("Validar Pago")
        if st.button("✅ Validar"):
            if op_id:
                exito, msg = verificar_pago_mp(op_id, user['id'])
                if exito: st.balloons(); st.success(msg); time.sleep(2); st.rerun()
                else: st.error(msg)
    if st.button("Salir"): st.session_state.user = None; st.rerun()

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum")

paises = list(ALBUM_PAGES.keys())
seleccion = st.selectbox("Selecciona Sección:", paises)
start, end = ALBUM_PAGES[seleccion]
numeros_posibles = list(range(start, end + 1))

# Obtenemos lo que TENEMOS (no lo que falta)
ids_tengo, repetidas_info = get_inventory_status(user['id'], start, end)

# Progreso Local
total_sec = end - start + 1
tengo_sec = len(ids_tengo)
st.progress(tengo_sec / total_sec, text=f"Tienes {tengo_sec} de {total_sec} figuritas")

# --- UI CASCADA (LÓGICA MEJORADA) ---
with st.form("album_logic_inverted"):
    
    st.markdown("### 1️⃣ ¿Cuáles TENÉS?")
    st.caption("Marca todas las que te salieron en el paquete.")
    # Selector de Posesión
    seleccion_tengo = st.pills(
        "Mis Figuritas", 
        numeros_posibles, 
        default=ids_tengo, 
        selection_mode="multi", 
        key="pills_tengo"
    )
    
    st.markdown("---")
    
    st.markdown("### 2️⃣ ¿Cuáles están REPETIDAS?")
    st.caption("De las que tienes arriba, marca las que te sobran.")
    
    # El selector de repetidas SOLO muestra las que marcaste arriba como "Tengo"
    # Si desmarcas arriba, desaparece de abajo automáticamente.
    posibles_repetidas = sorted(seleccion_tengo) if seleccion_tengo else []
    ids_repetidas_actuales = list(repetidas_info.keys())
    # Filtramos para que no queden IDs huerfanos si desmarcaste arriba
    ids_repetidas_validos = [ID for ID in ids_repetidas_actuales if ID in posibles_repetidas]
    
    seleccion_repes = st.pills(
        "Mis Repetidas", 
        posibles_repetidas, 
        default=ids_repetidas_validos, 
        selection_mode="multi", 
        key="pills_repes"
    )

    # Configuración de Precios (Solo si hay repetidas)
    edited_df = pd.DataFrame()
    if seleccion_repes:
        st.caption("💲 Configurar valores (Opcional)")
        ed_data = []
        for num in seleccion_repes:
            info = repetidas_info.get(num, {'price': 0})
            modo = "Venta" if info['price'] > 0 else "Canje"
            ed_data.append({"Figurita": num, "Modo": modo, "Precio": info['price']})
        
        edited_df = st.data_editor(pd.DataFrame(ed_data), column_config={
            "Figurita": st.column_config.NumberColumn(disabled=True),
            "Modo": st.column_config.SelectboxColumn(options=["Canje", "Venta"], required=True),
            "Precio": st.column_config.NumberColumn(min_value=0, step=100)
        }, hide_index=True, use_container_width=True)

    if st.form_submit_button("💾 Guardar Mi Álbum", use_container_width=True):
        save_inventory_inverted(user['id'], start, end, seleccion_tengo, edited_df)
        st.toast("¡Álbum Actualizado!", icon="✅"); time.sleep(1); st.rerun()

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