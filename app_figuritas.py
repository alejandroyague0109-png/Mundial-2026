import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Figus 26 | Intercambio Mundial", layout="wide", page_icon="⚽")

# Recuperamos las credenciales de los "Secrets" de Streamlit
# (Te enseñaré a configurar esto en el paso a paso luego)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. FUNCIONES DE BASE DE DATOS (CRUD) ---

def get_user_by_phone(phone):
    """Busca si el usuario ya existe por su teléfono"""
    response = supabase.table("users").select("*").eq("phone", phone).execute()
    if response.data:
        return response.data[0]
    return None

def create_user(nick, phone, zone):
    """Registra un nuevo usuario"""
    try:
        data = {"nick": nick, "phone": phone, "zone": zone}
        response = supabase.table("users").insert(data).execute()
        return response.data[0]
    except Exception as e:
        st.error(f"Error al crear usuario: {e}")
        return None

def get_inventory(user_id):
    """Descarga las figuritas del usuario"""
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    if df.empty:
        return [], {} # Faltantes (lista), Repetidas (dict {num: precio})
    
    faltantes = df[df['status'] == 'faltante']['sticker_num'].tolist()
    
    # Creamos un diccionario para las repetidas: {10: 500, 20: 0}
    repes_df = df[df['status'] == 'repetida']
    repetidas = dict(zip(repes_df['sticker_num'], repes_df['price']))
    
    return faltantes, repetidas

def update_inventory_item(user_id, sticker_num, status, price=0, action="add"):
    """Agrega o quita una figurita de Supabase"""
    try:
        if action == "add":
            data = {"user_id": user_id, "sticker_num": sticker_num, "status": status, "price": price}
            supabase.table("inventory").upsert(data).execute()
        elif action == "remove":
            supabase.table("inventory").delete().match({"user_id": user_id, "sticker_num": sticker_num, "status": status}).execute()
    except Exception as e:
        print(f"Error inventario: {e}")

def check_contact_limit(user):
    """Verifica si el usuario FREE puede ver otro contacto hoy"""
    if user['is_premium']:
        return True # Premium siempre puede
    
    hoy = str(date.today())
    # Si cambió el día, reseteamos contador
    if str(user['last_contact_date']) != hoy:
        supabase.table("users").update({"last_contact_date": hoy, "daily_contacts_count": 0}).eq("id", user['id']).execute()
        return True
    
    # Si es el mismo día, chequeamos límite (1 por día)
    if user['daily_contacts_count'] < 1:
        return True
    
    return False

def consume_contact_credit(user):
    """Descuenta 1 crédito al ver un contacto"""
    if not user['is_premium']:
        nuevo_count = user['daily_contacts_count'] + 1
        supabase.table("users").update({"daily_contacts_count": nuevo_count}).eq("id", user['id']).execute()
        # Actualizamos la sesión local para reflejar el cambio inmediato
        st.session_state.user['daily_contacts_count'] = nuevo_count

# --- 3. MOTORES DE MATCH (ALGORITMOS) ---

def fetch_all_market_data():
    """Trae TODOS los datos necesarios para calcular matches en memoria (más rápido que SQL complejo)"""
    # 1. Traer todos los inventarios excepto el mío
    mi_id = st.session_state.user['id']
    response = supabase.table("inventory").select("*, users(nick, zone, phone)").neq("user_id", mi_id).execute()
    return pd.DataFrame(response.data)

def find_matches(mis_faltas, mis_repes, market_df):
    """Encuentra Coincidencias Directas y Ventas"""
    directos = []
    ventas = []
    
    if market_df.empty: return [], []

    # Aplanar estructura de usuario
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone'] = market_df['users'].apply(lambda x: x['phone'])
    
    # Filtrar solo lo que YO necesito (Alguien tiene mis faltantes como 'repetida')
    ofertas_relevantes = market_df[
        (market_df['status'] == 'repetida') & 
        (market_df['sticker_num'].isin(mis_faltas))
    ]
    
    for _, row in ofertas_relevantes.iterrows():
        figu_id = row['sticker_num']
        precio = row['price']
        usuario_otro = row['user_id']
        
        match_obj = {
            'nick': row['nick'],
            'zone': row['zone'],
            'phone': row['phone'],
            'figu': figu_id,
            'price': precio
        }
        
        if precio > 0:
            # Es VENTA
            ventas.append(match_obj)
        else:
            # Es TRUEQUE (Solo si yo tengo algo para él)
            # Buscar qué le falta a este usuario específico
            sus_faltas = market_df[
                (market_df['user_id'] == usuario_otro) & 
                (market_df['status'] == 'faltante')
            ]['sticker_num'].tolist()
            
            # Intersección: Lo que yo tengo vs Lo que él busca
            cruce = set(mis_repes.keys()).intersection(set(sus_faltas))
            
            if cruce:
                match_obj['te_pide'] = list(cruce)[0] # Tomamos la primera coincidencia
                directos.append(match_obj)
                
    return directos, ventas

def find_triangulation(mis_faltas, mis_repes, market_df):
    """
    Algoritmo Premium: A -> B -> C -> A
    Busca cadenas de 3 usuarios.
    """
    triangulaciones = []
    if market_df.empty: return []
    
    # Pre-procesamiento de datos para velocidad
    # Diccionario: {user_id: {'repes': {num}, 'faltas': {num}, 'data': {...}}}
    users_map = {}
    
    # Llenamos el mapa
    for uid in market_df['user_id'].unique():
        u_rows = market_df[market_df['user_id'] == uid]
        repes = set(u_rows[u_rows['status'] == 'repetida']['sticker_num'])
        faltas = set(u_rows[u_rows['status'] == 'faltante']['sticker_num'])
        # Datos de contacto (tomamos de la primera fila)
        u_info = u_rows.iloc[0]['users']
        users_map[uid] = {'repes': repes, 'faltas': faltas, 'info': u_info}
        
    mis_faltas_set = set(mis_faltas)
    mis_repes_set = set(mis_repes.keys())

    # PASO 1: Buscar Candidato B (Tiene lo que yo quiero)
    for bid, b_data in users_map.items():
        lo_que_b_me_da = mis_faltas_set.intersection(b_data['repes'])
        if not lo_que_b_me_da: continue
        
        # PASO 2: Buscar Candidato C (Tiene lo que B quiere)
        for cid, c_data in users_map.items():
            if cid == bid: continue
            
            lo_que_c_da_a_b = b_data['faltas'].intersection(c_data['repes'])
            if not lo_que_c_da_a_b: continue
            
            # PASO 3: Ver si YO tengo lo que C quiere (Cerrar el círculo)
            lo_que_yo_doy_a_c = c_data['faltas'].intersection(mis_repes_set)
            
            if lo_que_yo_doy_a_c:
                # ¡Triangulación Encontrada!
                triangulaciones.append({
                    'paso1': f"Tú das **#{list(lo_que_yo_doy_a_c)[0]}** a {c_data['info']['nick']}",
                    'paso2': f"{c_data['info']['nick']} da **#{list(lo_que_c_da_a_b)[0]}** a {b_data['info']['nick']}",
                    'paso3': f"{b_data['info']['nick']} te da **#{list(lo_que_b_me_da)[0]}** a TI",
                    'contactos': [
                        {'nick': c_data['info']['nick'], 'tel': c_data['info']['phone'], 'rol': 'Intermediario'},
                        {'nick': b_data['info']['nick'], 'tel': b_data['info']['phone'], 'rol': 'Tiene tu figu'}
                    ]
                })
                if len(triangulaciones) >= 5: return triangulaciones # Límite para no saturar UI
                
    return triangulaciones

# --- 4. INTERFAZ DE USUARIO (UI) ---

# --- LOGIN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🏆 Figus 26 | Mendoza")
    st.markdown("### El mercado inteligente de figuritas")
    
    tab1, tab2 = st.tabs(["Ingresar", "Registrarse"])
    
    with tab1:
        phone_in = st.text_input("Tu Teléfono (ID Único)", placeholder="2611234567")
        if st.button("Entrar"):
            user = get_user_by_phone(phone_in)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuario no encontrado. Regístrate primero.")
    
    with tab2:
        new_nick = st.text_input("Tu Nickname (Alias)")
        new_phone = st.text_input("Tu Teléfono", placeholder="261...")
        new_zone = st.selectbox("Tu Zona Principal", ["Plaza Independencia", "Godoy Cruz", "Guaymallén", "Maipú", "Luján", "Las Heras"])
        
        if st.button("Crear Cuenta"):
            if get_user_by_phone(new_phone):
                st.warning("Este teléfono ya está registrado.")
            else:
                user = create_user(new_nick, new_phone, new_zone)
                if user:
                    st.success("¡Bienvenido! Ahora ingresa en la otra pestaña.")
    
    st.stop()

# --- APP PRINCIPAL (LOGUEADO) ---
user = st.session_state.user
mis_faltas, mis_repes = get_inventory(user['id'])

# BARRA LATERAL
with st.sidebar:
    st.header(f"Hola, {user['nick']} 👋")
    st.caption(f"Zona: {user['zone']}")
    status_label = "💎 PREMIUM" if user['is_premium'] else "👤 GRATIS"
    st.markdown(f"**Estado:** {status_label}")
    
    if not user['is_premium']:
        limit_txt = f"{user['daily_contacts_count']}/1 Contactos hoy"
        st.progress(user['daily_contacts_count']/1, text=limit_txt)
        if st.button("🚀 Pasar a Premium ($5000)"):
            st.info("Función simulada: ¡Imagina que vas a Mercado Pago!")
            # Simulación de pago exitoso
            supabase.table("users").update({"is_premium": True}).eq("id", user['id']).execute()
            st.session_state.user['is_premium'] = True
            st.rerun()

    st.divider()
    
    # GESTIÓN INVENTARIO
    st.subheader("🎒 Mi Mochila")
    
    with st.expander("➕ Agregar Repetida", expanded=True):
        r_num = st.number_input("Número #", 1, 900, key="r_n")
        r_tipo = st.radio("Objetivo:", ["Cambio ($0)", "Venta"], horizontal=True)
        r_precio = 0
        if r_tipo == "Venta":
            r_precio = st.number_input("Precio $", 100, 10000, step=100)
            
        if st.button("Guardar Repetida"):
            update_inventory_item(user['id'], r_num, "repetida", r_precio, "add")
            st.toast("Guardado!")
            st.rerun()

    with st.expander("➕ Agregar Faltante"):
        f_num = st.number_input("Me falta la #", 1, 900, key="f_n")
        if st.button("Guardar Deseo"):
            if f_num not in mis_faltas:
                update_inventory_item(user['id'], f_num, "faltante", 0, "add")
                st.toast("Guardado!")
                st.rerun()

    st.markdown("---")
    if st.button("Cerrar Sesión"):
        st.session_state.user = None
        st.rerun()

# PANTALLA PRINCIPAL
st.title("Mercado de Oportunidades")
st.info(f"Buscas **{len(mis_faltas)}** figuritas | Ofreces **{len(mis_repes)}**")

# Carga de datos del mercado
market_df = fetch_all_market_data()
directos, ventas = find_matches(mis_faltas, mis_repes, market_df)

tab_canje, tab_compra, tab_tri = st.tabs(["🤝 Canje Directo", "💰 Compra", "⚡ Triangulación (Pro)"])

# --- TAB 1: CANJE DIRECTO ---
with tab_canje:
    if not directos:
        st.write("No hay coincidencias directas por ahora.")
    else:
        for m in directos:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{m['nick']}** ({m['zone']}) cambia la **#{m['figu']}** por tu **#{m['te_pide']}**")
                
                # Botón de Contacto con Lógica Freemium
                if c2.button("WhatsApp", key=f"d_{m['phone']}_{m['figu']}"):
                    if check_contact_limit(user):
                        consume_contact_credit(user)
                        msg = f"Hola {m['nick']}, cambiamos mi {m['te_pide']} por tu {m['figu']}?"
                        link = f"https://wa.me/549{m['phone']}?text={msg.replace(' ', '%20')}"
                        st.markdown(f"[Abrir Chat]({link})")
                    else:
                        st.error("🔒 Límite diario alcanzado. Hazte Premium.")

                if c2.button("✅ ¡Ya la tengo!", key=f"ok_d_{m['figu']}"):
                    update_inventory_item(user['id'], m['figu'], "faltante", action="remove") # Borro mi falta
                    update_inventory_item(user['id'], m['te_pide'], "repetida", action="remove") # Borro mi repe
                    st.success("Inventario actualizado.")
                    st.rerun()

# --- TAB 2: COMPRA ---
with tab_compra:
    if not ventas:
        st.write("Nadie vende lo que buscas.")
    else:
        for v in ventas:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{v['nick']}** vende la **#{v['figu']}** a **${v['price']}**")
                
                if c2.button("WhatsApp", key=f"v_{v['phone']}_{v['figu']}"):
                    if check_contact_limit(user):
                        consume_contact_credit(user)
                        msg = f"Hola {v['nick']}, te compro la {v['figu']}."
                        link = f"https://wa.me/549{v['phone']}?text={msg.replace(' ', '%20')}"
                        st.markdown(f"[Abrir Chat]({link})")
                    else:
                        st.error("🔒 Límite diario alcanzado.")

                if c2.button("✅ Comprada", key=f"ok_v_{v['figu']}"):
                    update_inventory_item(user['id'], v['figu'], "faltante", action="remove")
                    st.success("Borrada de tus faltantes.")
                    st.rerun()

# --- TAB 3: TRIANGULACIÓN (PREMIUM) ---
with tab_tri:
    if not user['is_premium']:
        st.warning("🔒 Esta función es exclusiva para usuarios PREMIUM.")
        st.markdown("El algoritmo ha detectado **posibles cadenas de 3 pasos** para conseguir tus figuritas, pero están ocultas.")
        st.markdown("Desbloquea por el precio de 2 paquetes de figuritas.")
    else:
        triangulaciones = find_triangulation(mis_faltas, mis_repes, market_df)
        if not triangulaciones:
            st.info("El algoritmo buscó en profundidad pero no encontró cadenas de 3 hoy.")
        else:
            for i, t in enumerate(triangulaciones):
                with st.container(border=True):
                    st.markdown(f"### ⚡ Oportunidad #{i+1}")
                    st.write(t['paso1'])
                    st.write(t['paso2'])
                    st.write(t['paso3'])
                    st.divider()
                    c1, c2 = st.columns(2)
                    for idx, contacto in enumerate(t['contactos']):
                        col = c1 if idx == 0 else c2
                        msg = f"Hola {contacto['nick']}, vi una triangulación en la App Figus26."
                        link = f"https://wa.me/549{contacto['tel']}?text={msg.replace(' ', '%20')}"
                        col.markdown(f"**{contacto['rol']}:** [{contacto['nick']}]({link})")