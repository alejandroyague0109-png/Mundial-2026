import streamlit as st
import pandas as pd
from supabase import create_client, Client
import mercadopago
from datetime import date
import time
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
    if not clean_phone: return None, "Che, poné un teléfono válido."
    phone_hash = utils.hash_phone_searchable(phone)
    try:
        response = supabase.table("users").select("*").eq("phone_hash", phone_hash).execute()
        if not response.data: return None, "No te tengo registrado. ¿Te creaste la cuenta?"
        user = response.data[0]
        if utils.check_password(password, user['password']): return user, "OK"
        else: return None, "La contraseña no va. Probá de nuevo."
    except Exception as e:
        return None, "Se cayó la conexión. Probá en un toque."

def register_user(nick, phone, province, zone, password, secret_q, secret_a):
    if not utils.validar_formato_telefono(phone): return None, "El teléfono está mal escrito."
    if not nick or not password or not province or not zone: 
        return None, "Faltan datos obligatorios."
    if not secret_q or not secret_a:
        return None, "La pregunta de seguridad es obligatoria."

    p_hash = utils.hash_phone_searchable(phone)
    p_enc = utils.encrypt_phone(phone)
    a_hash = utils.hash_password(secret_a.lower().strip())

    try:
        if supabase.table("users").select("*").eq("phone_hash", p_hash).execute().data: 
            return None, "Ese número ya está registrado, crack."
        
        hashed_pw = utils.hash_password(password)
        
        data = {
            "nick": nick, 
            "phone_hash": p_hash,
            "phone_encrypted": p_enc,
            "province": province, 
            "zone": zone, 
            "password": hashed_pw,
            "secret_question": secret_q,
            "secret_answer": a_hash,
            "is_admin": (utils.limpiar_telefono(phone) == config.ADMIN_PHONE), 
            "reputation": 0, "daily_contacts_count": 0, "last_contact_date": str(date.today())
        }
        response = supabase.table("users").insert(data).execute()
        return response.data[0], "OK"
    except Exception as e: return None, f"Error DB: {str(e)}"

# --- RECUPERACIÓN ---
def get_security_info(phone):
    clean_phone = utils.limpiar_telefono(phone)
    if not clean_phone: return None, "Teléfono inválido."
    p_hash = utils.hash_phone_searchable(phone)
    try:
        resp = supabase.table("users").select("secret_question, secret_answer").eq("phone_hash", p_hash).execute()
        if resp.data: return resp.data[0], "OK"
        return None, "No encontré ese número."
    except: return None, "Error de conexión."

def reset_password(phone, answer_input, new_password):
    if not new_password: return False, "La nueva contraseña no puede estar vacía."
    p_hash = utils.hash_phone_searchable(phone)
    try:
        resp = supabase.table("users").select("secret_answer").eq("phone_hash", p_hash).execute()
        if not resp.data: return False, "Usuario no encontrado."
        real_answer_hash = resp.data[0]['secret_answer']
        if utils.check_password(answer_input.lower().strip(), real_answer_hash):
            new_pw_hash = utils.hash_password(new_password)
            supabase.table("users").update({"password": new_pw_hash}).eq("phone_hash", p_hash).execute()
            return True, "¡Contraseña cambiada! Ahora iniciá sesión."
        else: return False, "Respuesta incorrecta."
    except Exception as e: return False, str(e)

# --- EDICIÓN DE PERFIL ---
def update_profile(user_id, province, zone):
    try:
        supabase.table("users").update({
            "province": province, 
            "zone": zone
        }).eq("id", user_id).execute()
        return True, "Perfil actualizado correctamente."
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

# --- CONTACTOS ---
def log_unlock(user_id, target_id):
    try:
        supabase.table("contact_logs").insert({"user_id": user_id, "target_id": target_id}).execute()
        return True
    except: return False

def get_unlocked_ids(user_id):
    try:
        resp = supabase.table("contact_logs").select("target_id").eq("user_id", user_id).execute()
        return {item['target_id'] for item in resp.data}
    except: return set()

def remove_unlock(user_id, target_id):
    try:
        supabase.table("contact_logs").delete().eq("user_id", user_id).eq("target_id", target_id).execute()
        return True
    except: return False

# --- INVENTARIO (Tu versión original estable) ---
def get_inventory_status(user_id, start, end):
    try:
        response = supabase.table("inventory").select("*").eq("user_id", user_id).execute()
        df = pd.DataFrame(response.data)
        if df.empty: df = pd.DataFrame(columns=['sticker_num', 'status', 'price', 'quantity', 'user_id'])
        else:
            df['sticker_num'] = pd.to_numeric(df['sticker_num'], errors='coerce').fillna(0).astype(int)
        
        db_tengo = []
        db_wishlist = []
        db_repetidas_info = {}
        
        if not df.empty:
            mask = (df['sticker_num'] >= start) & (df['sticker_num'] <= end)
            df_page = df[mask]
            db_tengo = df_page[df_page['status'] == 'tengo']['sticker_num'].tolist()
            db_wishlist = df_page[df_page['status'] == 'wishlist']['sticker_num'].tolist()
            for _, row in df_page[df_page['status'] == 'repetida'].iterrows():
                qty = row.get('quantity', 1)
                if pd.isna(qty): qty = 1
                db_repetidas_info[row['sticker_num']] = {'price': row['price'], 'quantity': int(qty)}
                if row['sticker_num'] not in db_tengo: db_tengo.append(row['sticker_num'])
        return db_tengo, db_wishlist, db_repetidas_info, df
    except Exception: return [], [], {}, pd.DataFrame()

def save_inventory_positive(user_id, start, end, ui_owned_list, ui_wishlist_list, ui_repe_df):
    page_numbers = list(range(start, end + 1))
    max_retries = 3
    for attempt in range(max_retries):
        try:
            supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", page_numbers).execute()
            break 
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(1); continue
            else: st.error("Error de conexión."); raise e

    new_rows = []
    for num in ui_owned_list:
        new_rows.append({"user_id": user_id, "sticker_num": num, "status": "tengo", "price": 0, "quantity": 1})
    for num in ui_wishlist_list:
        if num not in ui_owned_list:
            new_rows.append({"user_id": user_id, "sticker_num": num, "status": "wishlist", "price": 0, "quantity": 1})
    if not ui_repe_df.empty:
        for _, row in ui_repe_df.iterrows():
            es_venta = "Venta" in str(row['Modo'])
            qty = int(row.get('Cantidad', 1))
            new_rows.append({"user_id": user_id, "sticker_num": row['Figurita'], "status": "repetida", "price": int(row['Precio']) if es_venta else 0, "quantity": qty})
    
    if new_rows:
        for attempt in range(max_retries):
            try:
                supabase.table("inventory").insert(new_rows).execute()
                break
            except Exception as e:
                if attempt < max_retries - 1: time.sleep(1)
                else: raise e
    
    # Limpiamos caché del mercado
    fetch_market.clear()

def get_full_wishlist(user_id):
    try:
        resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "wishlist").execute()
        return sorted([int(x['sticker_num']) for x in resp.data])
    except: return []

# --- GESTIÓN DE SOLICITUDES ---
def get_pending_transactions(user_id):
    try:
        resp = supabase.table("transaction_requests").select("*, users!sender_id(nick)").eq("receiver_id", user_id).eq("status", "pending").execute()
        return resp.data
    except Exception as e: return []

def confirm_transaction_request(request_id, user_id_receiver):
    try:
        req = supabase.table("transaction_requests").select("*").eq("id", request_id).execute().data[0]
        type_tx = req['type']
        fig_sent_by_sender = req['fig_sent']
        fig_received_by_sender = req['fig_received']
        
        if fig_received_by_sender:
            target_fig = int(fig_received_by_sender)
            resp = supabase.table("inventory").select("*").eq("user_id", user_id_receiver).eq("sticker_num", target_fig).eq("status", "repetida").execute()
            if resp.data:
                row = resp.data[0]
                curr = int(row.get('quantity') or 1)
                if curr > 1: supabase.table("inventory").update({"quantity": curr - 1}).eq("id", row['id']).execute()
                else: supabase.table("inventory").delete().eq("id", row['id']).execute()
        
        if type_tx == 'exchange' and fig_sent_by_sender:
            target_get = int(fig_sent_by_sender)
            supabase.table("inventory").delete().eq("user_id", user_id_receiver).eq("sticker_num", target_get).eq("status", "wishlist").execute()
            check = supabase.table("inventory").select("*").eq("user_id", user_id_receiver).eq("sticker_num", target_get).eq("status", "tengo").execute()
            if not check.data: supabase.table("inventory").insert({"user_id": user_id_receiver, "sticker_num": target_get, "status": "tengo", "price": 0, "quantity": 1}).execute()

        supabase.table("transaction_requests").update({"status": "accepted"}).eq("id", request_id).execute()
        remove_unlock(user_id_receiver, req['sender_id'])
        fetch_market.clear()
        return True, "Confirmado: Tu inventario se actualizó."
    except Exception as e: return False, str(e)

def reject_transaction_request(request_id):
    try:
        supabase.table("transaction_requests").delete().eq("id", request_id).execute()
        return True
    except: return False

# --- INTERCAMBIO ---
def register_exchange(user_id, given_fig, received_fig, target_id_to_remove=None):
    try:
        given_fig = int(given_fig)
        received_fig = int(received_fig)
        resp = supabase.table("inventory").select("*").eq("user_id", user_id).eq("sticker_num", given_fig).eq("status", "repetida").execute()
        if not resp.data: return False, f"No tenés la #{given_fig} repetida."
        row = resp.data[0]
        current_qty = int(row.get('quantity') or 1)
        if current_qty > 1: supabase.table("inventory").update({"quantity": current_qty - 1}).eq("id", row['id']).execute()
        else: supabase.table("inventory").delete().eq("id", row['id']).execute()
        supabase.table("inventory").delete().eq("user_id", user_id).eq("sticker_num", received_fig).eq("status", "wishlist").execute()
        check = supabase.table("inventory").select("*").eq("user_id", user_id).eq("sticker_num", received_fig).eq("status", "tengo").execute()
        if not check.data: supabase.table("inventory").insert({"user_id": user_id, "sticker_num": received_fig, "status": "tengo", "price": 0, "quantity": 1}).execute()
        if target_id_to_remove:
            supabase.table("transaction_requests").insert({"sender_id": user_id, "receiver_id": target_id_to_remove, "fig_sent": given_fig, "fig_received": received_fig, "type": "exchange"}).execute()
            remove_unlock(user_id, target_id_to_remove)
        fetch_market.clear()
        return True, f"¡Listo! Actualicé tu álbum y le mandé la confirmación al otro usuario."
    except Exception as e: return False, f"Error: {str(e)}"

def register_purchase(user_id, received_fig, target_id_to_remove=None):
    try:
        received_fig = int(received_fig)
        supabase.table("inventory").delete().eq("user_id", user_id).eq("sticker_num", received_fig).eq("status", "wishlist").execute()
        check = supabase.table("inventory").select("*").eq("user_id", user_id).eq("sticker_num", received_fig).eq("status", "tengo").execute()
        if not check.data: supabase.table("inventory").insert({"user_id": user_id, "sticker_num": received_fig, "status": "tengo", "price": 0, "quantity": 1}).execute()
        if target_id_to_remove:
            supabase.table("transaction_requests").insert({"sender_id": user_id, "receiver_id": target_id_to_remove, "fig_sent": None, "fig_received": received_fig, "type": "purchase"}).execute()
            remove_unlock(user_id, target_id_to_remove)
        fetch_market.clear()
        return True, "¡Compra registrada! Le avisé al vendedor para que actualice su stock."
    except Exception as e: return False, f"Error: {str(e)}"

# --- MERCADO ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_market(user_id):
    try:
        resp = supabase.table("inventory").select("*, users(nick, province, zone, phone_encrypted, reputation)").neq("user_id", user_id).execute()
        df = pd.DataFrame(resp.data)
        if not df.empty:
            df['sticker_num'] = pd.to_numeric(df['sticker_num'], errors='coerce').fillna(0).astype(int)
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def find_matches(user_id, market_df):
    if market_df.empty: return [], []
    
    # FIX PANDAS: Agregamos copy() aquí para arreglar el error del dataframe
    market_df = market_df.copy()

    try:
        resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "tengo").execute()
        mis_tengo_set = set(int(item['sticker_num']) for item in resp.data)
        resp_r = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "repetida").execute()
        mis_repes_set = set(int(item['sticker_num']) for item in resp_r.data)
        resp_w = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "wishlist").execute()
        mis_wishlist_set = set(int(item['sticker_num']) for item in resp_w.data)
    except: return [], []

    directos, ventas = [], []
    market_df['nick'] = market_df['users'].apply(lambda x: x['nick'])
    market_df['province'] = market_df['users'].apply(lambda x: x.get('province', 'Mendoza'))
    market_df['zone'] = market_df['users'].apply(lambda x: x['zone'])
    market_df['phone_encrypted'] = market_df['users'].apply(lambda x: x.get('phone_encrypted', ''))
    market_df['reputation'] = market_df['users'].apply(lambda x: x.get('reputation', 0))
    market_df['other_id'] = market_df['users'].apply(lambda x: x.get('id', 0))
    
    ofertas = market_df[market_df['status'] == 'repetida']
    
    for _, row in ofertas.iterrows():
        figu = int(row['sticker_num'])
        if figu not in mis_tengo_set:
            es_wishlist = figu in mis_wishlist_set
            match = {'nick': row['nick'], 'province': row['province'], 'zone': row['zone'], 'phone_encrypted': row['phone_encrypted'], 'figu': figu, 'price': row['price'], 'reputation': row['reputation'], 'target_id': row['user_id'], 'is_wishlist': es_wishlist}
            if row['price'] > 0: ventas.append(match)
            else:
                sus_tengo_df = market_df[(market_df['user_id'] == row['user_id']) & (market_df['status'] == 'tengo')]
                sus_tengo_set = set(sus_tengo_df['sticker_num'].tolist())
                sirven = [r for r in mis_repes_set if r not in sus_tengo_set]
                if sirven:
                    match['te_pide'] = sirven[0]
                    directos.append(match)
    
    directos.sort(key=lambda x: (not x['is_wishlist'], -x['reputation']))
    ventas.sort(key=lambda x: (not x['is_wishlist'], x['price'], -x['reputation']))
    return directos, ventas

# --- UTILS ---
def verificar_pago_mp(payment_id, user_id):
    try:
        if supabase.table("payments_log").select("*").eq("payment_id", payment_id).execute().data: return False, "Usado."
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 404: return False, "No encontrado."
        resp = payment_info["response"]
        if resp.get("status") == "approved" and resp.get("transaction_amount") >= config.PRECIO_PREMIUM:
            supabase.table("payments_log").insert({"payment_id": str(payment_id), "user_id": user_id, "amount": resp.get("transaction_amount"), "status": "approved"}).execute()
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Sos Premium!"
        else: return False, "Pago pendiente/rechazado."
    except Exception as e: return False, str(e)

def votar_usuario(voter_id, target_id):
    if voter_id == target_id: return False, "No autovoto."
    try:
        check = supabase.table("votes").select("*").eq("voter_id", voter_id).eq("target_id", target_id).execute()
        if check.data: return False, "Ya votaste."
        supabase.table("votes").insert({"voter_id": voter_id, "target_id": target_id}).execute()
        curr_rep = supabase.table("users").select("reputation").eq("id", target_id).execute().data[0]['reputation'] or 0
        supabase.table("users").update({"reputation": curr_rep + 1}).eq("id", target_id).execute()
        return True, "¡Este sí es Fair Player!"
    except Exception as e: return False, str(e)

def verify_daily_reset(user):
    if not user: return False
    try:
        hoy = str(date.today())
        last_date = str(user.get('last_contact_date', ''))
        if last_date != hoy:
            supabase.table("users").update({"last_contact_date": hoy, "daily_contacts_count": 0}).eq("id", user['id']).execute()
            user['last_contact_date'] = hoy
            user['daily_contacts_count'] = 0
            return True
    except: pass
    return False

def check_contact_limit(user):
    if verify_daily_reset(user): return True
    if user.get('is_premium', False): return True
    return user.get('daily_contacts_count', 0) < 1

def consume_credit(user):
    if not user.get('is_premium', False):
        try:
            nuevo = user.get('daily_contacts_count', 0) + 1
            supabase.table("users").update({"daily_contacts_count": nuevo}).eq("id", user['id']).execute()
            if 'user' in st.session_state: st.session_state.user['daily_contacts_count'] = nuevo
        except: pass

def process_csv_upload(df, user_id):
    try:
        df.columns = [c.lower().strip() for c in df.columns]
        expected_cols = ['num', 'status', 'price']
        if not all(col in df.columns for col in expected_cols): return False, "CSV inválido."
        rows_to_insert = []
        for _, row in df.iterrows():
            st_val = str(row['status']).lower().strip()
            if st_val not in ['tengo', 'repetida', 'wishlist']: st_val = 'tengo'
            qty = 1
            if 'quantity' in df.columns and pd.notnull(row['quantity']): qty = int(row['quantity'])
            rows_to_insert.append({"user_id": user_id, "sticker_num": int(row['num']), "status": st_val, "price": int(row['price']) if pd.notnull(row['price']) else 0, "quantity": qty})
        if rows_to_insert:
            nums = [r['sticker_num'] for r in rows_to_insert]
            supabase.table("inventory").delete().eq("user_id", user_id).in_("sticker_num", nums).execute()
            supabase.table("inventory").insert(rows_to_insert).execute()
            fetch_market.clear()
            return True, f"Cargadas {len(rows_to_insert)}."
        return False, "CSV vacío."
    except Exception as e: return False, str(e)

def get_user_by_id(user_id):
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data: return response.data[0]
        return None
    except: return None

# --- FUNCIONES DE SOPORTE PARA TRIANGULACIÓN (NUEVAS: AGREGADAS AL FINAL) ---
def get_users_with_sticker(figu_num):
    """Busca usuarios con la figurita y devuelve phone_encrypted."""
    try:
        # Usamos sticker_num como en el resto de tu backup
        response = supabase.table("inventory")\
            .select("user_id, status, users(nick, province, zone, phone_encrypted)")\
            .eq("sticker_num", figu_num)\
            .execute()
        users = []
        for row in response.data:
            if not row.get('users'): continue
            raw_status = str(row.get('status', '')).lower().strip()
            if raw_status in ["repetida", "repe"]:
                u_data = row.get('users', {})
                users.append({
                    'user_id': row['user_id'],
                    'nick': u_data.get('nick', 'User'),
                    'province': str(u_data.get('province', '')).strip(),
                    'zone': str(u_data.get('zone', '')).strip(),
                    'phone_encrypted': u_data.get('phone_encrypted', '')
                })
        return users
    except Exception as e: return []

def get_wishlists_of_users(user_ids):
    try:
        if not user_ids: return {}
        response = supabase.table("inventory").select("user_id, sticker_num").in_("user_id", user_ids).eq("status", "wishlist").execute()
        res = {}
        for row in response.data:
            uid = row['user_id']
            if uid not in res: res[uid] = []
            res[uid].append(row['sticker_num'])
        return res
    except: return {}

def find_potential_bridges(needed_figus, my_repes):
    try:
        if not needed_figus or not my_repes: return []
        holders = supabase.table("inventory").select("user_id, sticker_num, status, users(nick, province, zone, phone_encrypted)").in_("sticker_num", needed_figus).execute()
        holder_map = {} 
        user_info = {}
        candidate_ids = []
        
        for row in holders.data:
            if str(row.get('status', '')).lower().strip() not in ["repetida", "repe"]: continue
            uid = row['user_id']
            u_data = row.get('users', {})
            if uid not in holder_map: 
                holder_map[uid] = []
                candidate_ids.append(uid)
                user_info[uid] = {
                    'nick': u_data.get('nick', 'Puente'),
                    'province': str(u_data.get('province', '')).strip(),
                    'zone': str(u_data.get('zone', '')).strip(),
                    'phone_encrypted': u_data.get('phone_encrypted', '')
                }
            holder_map[uid].append(row['sticker_num'])
            
        if not candidate_ids: return []
        
        wanters = supabase.table("inventory").select("user_id, sticker_num").in_("user_id", candidate_ids).in_("sticker_num", my_repes).eq("status", "wishlist").execute()
        bridges = []
        for row in wanters.data:
            uid = row['user_id']
            if uid in holder_map:
                for has in holder_map[uid]:
                    bridges.append({
                        'user_id': uid, 'nick': user_info[uid]['nick'],
                        'province': user_info[uid]['province'], 'zone': user_info[uid]['zone'],
                        'phone_encrypted': user_info[uid]['phone_encrypted'],
                        'has_figu': has, 'wants_figu': row['sticker_num']
                    })
        return bridges
    except: return []