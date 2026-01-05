import streamlit as st
import pandas as pd
from supabase import create_client, Client
import mercadopago
from datetime import date
import config 
import utils

# --- CONEXIÓN ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    mp_token = st.secrets["MP_ACCESS_TOKEN"]
    supabase: Client = create_client(url, key)
    sdk = mercadopago.SDK(mp_token)
except Exception as e:
    st.error(f"Error de conexión DB/MP: {e}")
    st.stop()

# --- USUARIOS ---
def login_user(phone, password):
    clean_phone = utils.limpiar_telefono(phone)
    if not clean_phone: return None, "Ingresa un teléfono."
    response = supabase.table("users").select("*").eq("phone", clean_phone).execute()
    if not response.data: return None, "Usuario no encontrado."
    user = response.data[0]
    if utils.check_password(password, user['password']): return user, "OK"
    else: return None, "Contraseña incorrecta."

def register_user(nick, phone, zone, password):
    clean_phone = utils.limpiar_telefono(phone)
    if not utils.validar_formato_telefono(clean_phone): return None, "Teléfono inválido."
    if not nick or not password: return None, "Falta datos."
    if supabase.table("users").select("*").eq("phone", clean_phone).execute().data: return None, "Ya registrado."
    try:
        hashed_pw = utils.hash_password(password)
        data = {
            "nick": nick, "phone": clean_phone, "zone": zone, 
            "password": hashed_pw, 
            "is_admin": (clean_phone == config.ADMIN_PHONE), 
            "reputation": 0, "daily_contacts_count": 0, "last_contact_date": str(date.today())
        }
        response = supabase.table("users").insert(data).execute()
        return response.data[0], "OK"
    except Exception as e: return None, str(e)

# --- INVENTARIO (CON CANTIDADES) ---
def get_inventory_status(user_id, start, end):
    response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
    df = pd.DataFrame(response.data)
    if df.empty: df = pd.DataFrame(columns=['sticker_num', 'status', 'price', 'quantity', 'user_id'])
    
    db_tengo = []
    db_repetidas_info = {}
    
    if not df.empty:
        mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
        df_page = df[mask]
        
        # Lista simple de lo que tengo
        db_tengo = df_page[df_page['status'] == 'tengo']['sticker_num'].tolist()
        
        # Diccionario detallado de repetidas
        for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
            qty = row.get('quantity', 1)
            if pd.isna(qty): qty = 1
            db_repetidas_info[row['sticker_num']] = {'price': row['price'], 'quantity': int(qty)}
            
            # Si es repetida, también cuenta como "Tengo" visualmente
            if row['sticker_num'] not in db_tengo: db_tengo.append(row['sticker_num'])
            
    return db_tengo, db_repetidas_info, df

def save_inventory_positive(user_id, start, end, ui_owned_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
    new_rows = []
    
    # 1. Guardar TENGO
    for num in ui_owned_list:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "tengo", "price": 0, "quantity": 1})
        
    # 2. Guardar REPETIDAS (Sobreescribe si estaba en tengo)
    if not ui_repe_df.empty:
        for _, row in ui_repe_df.iterrows():
            es_venta = "Venta" in str(row['Modo'])
            qty = int(row.get('Cantidad', 1))
            new_rows.append({
                "user_id": user_id, "sticker_num": row['Figurita'], 
                "status": "repetida", "price": int(row['Precio']) if es_venta else 0,
                "quantity": qty
            })
    if new_rows: supabase.table("inventory").insert(new_rows).execute()

# --- INTERCAMBIO (Lógica Core) ---
def register_exchange(user_id, given_fig, received_fig):
    """
    1. Resta 1 a la repetida que entregas. Si llega a 0, la borra.
    2. Agrega la nueva como 'tengo' (verde).
    """
    try:
        # A. GESTIONAR LA QUE ENTREGO (REPETIDA)
        resp = supabase.table("inventory").select("*").eq("user_id", user_id).eq("sticker_num", given_fig).eq("status", "repetida").execute()
        
        if resp.data:
            row = resp.data[0]
            current_qty = row.get('quantity', 1) or 1
            
            if current_qty > 1:
                # Restar cantidad
                supabase.table("inventory").update({"quantity": current_qty - 1}).eq("id", row['id']).execute()
            else:
                # Borrar fila (desaparece de repetidas)
                supabase.table("inventory").delete().eq("id", row['id']).execute()
        
        # B. GESTIONAR LA QUE RECIBO (NUEVA)
        check = supabase.table("inventory").select("*").eq("user_id", user_id).eq("sticker_num", received_fig).eq("status", "tengo").execute()
        
        if not check.data:
            # La agrego a mi álbum
            supabase.table("inventory").insert({
                "user_id": user_id, "sticker_num": received_fig,
                "status": "tengo", "price": 0, "quantity": 1
            }).execute()
            
        return True, f"¡Hecho! Entregaste la #{given_fig} y ya marcamos la #{received_fig} en tu álbum."
    except Exception as e:
        return False, str(e)

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

def verificar_pago_mp(payment_id, user_id):
    try:
        if supabase.table("payments_log").select("*").eq("payment_id", payment_id).execute().data: return False, "Comprobante ya usado."
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 404: return False, "ID no encontrado."
        resp = payment_info["response"]
        if resp.get("status") == "approved" and resp.get("transaction_amount") >= config.PRECIO_PREMIUM:
            supabase.table("payments_log").insert({"payment_id": str(payment_id), "user_id": user_id, "amount": resp.get("transaction_amount"), "status": "approved"}).execute()
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Premium Activado!"
        else: return False, "Pago no aprobado."
    except Exception as e: return False, str(e)

def votar_usuario(voter_id, target_id):
    if voter_id == target_id: return False, "No autovoto."
    check = supabase.table("votes").select("*").eq("voter_id", voter_id).eq("target_id", target_id).execute()
    if check.data: return False, "Ya votaste."
    try:
        supabase.table("votes").insert({"voter_id": voter_id, "target_id": target_id}).execute()
        curr_rep = supabase.table("users").select("reputation").eq("id", target_id).execute().data[0]['reputation'] or 0
        supabase.table("users").update({"reputation": curr_rep + 1}).eq("id", target_id).execute()
        return True, "¡Recomendación enviada!"
    except Exception as e: return False, str(e)

def check_contact_limit(user):
    if user.get('is_premium', False): return True
    hoy = str(date.today())
    last_date = str(user.get('last_contact_date', ''))
    if last_date != hoy:
        supabase.table("users").update({"last_contact_date": hoy, "daily_contacts_count": 0}).eq("id", user['id']).execute()
        user['daily_contacts_count'] = 0
        user['last_contact_date'] = hoy
        return True
    return user.get('daily_contacts_count', 0) < 1

def consume_credit(user):
    if not user.get('is_premium', False):
        nuevo = user.get('daily_contacts_count', 0) + 1
        supabase.table("users").update({"daily_contacts_count": nuevo}).eq("id", user['id']).execute()
        if 'user' in st.session_state: st.session_state.user['daily_contacts_count'] = nuevo

def process_csv_upload(df, user_id):
    try:
        df.columns = [c.lower().strip() for c in df.columns]
        expected_cols = ['num', 'status', 'price']
        if not all(col in df.columns for col in expected_cols): return False, "CSV inválido."
        rows_to_insert = []
        for _, row in df.iterrows():
            st_val = str(row['status']).lower().strip()
            if st_val not in ['tengo', 'repetida']: st_val = 'tengo'
            qty = 1
            if 'quantity' in df.columns and pd.notnull(row['quantity']): qty = int(row['quantity'])
            rows_to_insert.append({
                "user_id": user_id, "sticker_num": int(row['num']),
                "status": st_val, "price": int(row['price']) if pd.notnull(row['price']) else 0,
                "quantity": qty
            })
        if rows_to_insert:
            nums = [r['sticker_num'] for r in rows_to_insert]
            supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", nums).execute()
            supabase.table("inventory").insert(rows_to_insert).execute()
            return True, f"Cargadas {len(rows_to_insert)}."
        return False, "CSV vacío."
    except Exception as e: return False, str(e)