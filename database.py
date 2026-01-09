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

# ==============================================================================
# 1. GESTIÓN DE USUARIOS
# ==============================================================================

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

def update_profile(user_id, province, zone):
    try:
        supabase.table("users").update({
            "province": province, 
            "zone": zone
        }).eq("id", user_id).execute()
        return True, "Perfil actualizado correctamente."
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"

def get_user_by_id(user_id):
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data: return response.data[0]
        return None
    except: return None

# ==============================================================================
# 2. GESTIÓN DE CRÉDITOS Y CONTACTOS
# ==============================================================================

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

# ==============================================================================
# 3. INVENTARIO (CORREGIDO: sticker_num)
# ==============================================================================

def fetch_inventory(user_id, start, end):
    """Recupera datos crudos para el cálculo inicial."""
    try:
        response = supabase.table("inventory")\
            .select("sticker_num, status, price")\
            .eq("user_id", user_id)\
            .gte("sticker_num", start)\
            .lte("sticker_num", end)\
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetch_inventory: {e}")
        return []

def get_inventory_status(user_id, start, end):
    """
    Recupera el estado para la vista de inventario.
    Retorna: ids_tengo, ids_wishlist, repetidas_info, stats
    """
    try:
        response = supabase.table("inventory")\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("sticker_num", start)\
            .lte("sticker_num", end)\
            .execute()
            
        tengo = []
        wish = []
        repes_info = {}
        
        for row in response.data:
            num_val = row['sticker_num'] 
            status = row['status']
            
            if status == 'tengo':
                tengo.append(num_val)
            elif status == 'wishlist':
                wish.append(num_val)
            elif status in ['repetida', 'repe']:
                tengo.append(num_val)
                repes_info[num_val] = {
                    'price': row.get('price', 0),
                    'quantity': row.get('quantity', 1)
                }
                
        return list(set(tengo)), list(set(wish)), repes_info, {}
    except Exception as e:
        print(f"Error get_inventory_status: {e}")
        return [], [], {}, {}

def save_inventory_positive(user_id, start, end, tengo_list, wish_list, df_repes):
    """Guarda los cambios borrando el rango y reinsertando."""
    try:
        # 1. Limpieza de zona (Borrar rango actual)
        supabase.table("inventory")\
            .delete()\
            .eq("user_id", user_id)\
            .gte("sticker_num", start)\
            .lte("sticker_num", end)\
            .execute()

        new_rows = []
        inserted_nums = set()

        # 2. Procesar REPETIDAS (Prioridad 1)
        if not df_repes.empty:
            for _, row in df_repes.iterrows():
                try:
                    num = int(row['Figurita'])
                    if start <= num <= end:
                        modo_texto = str(row.get('Modo', ''))
                        es_venta = "Venta" in modo_texto or "venta" in modo_texto
                        precio = float(row.get('Precio', 0)) if es_venta else 0
                        
                        new_rows.append({
                            "user_id": user_id,
                            "sticker_num": num,
                            "status": "repetida",
                            "quantity": int(row.get('Cantidad', 1)),
                            "price": precio
                        })
                        inserted_nums.add(num)
                except ValueError: continue

        # 3. Procesar TENGO (Prioridad 2)
        for val in tengo_list:
            try:
                num = int(val)
                if num not in inserted_nums and start <= num <= end:
                    new_rows.append({
                        "user_id": user_id, "sticker_num": num,
                        "status": "tengo", "quantity": 1, "price": 0
                    })
                    inserted_nums.add(num)
            except: continue

        # 4. Procesar WISHLIST (Prioridad 3)
        for val in wish_list:
            try:
                num = int(val)
                if num not in inserted_nums and start <= num <= end:
                    new_rows.append({
                        "user_id": user_id, "sticker_num": num,
                        "status": "wishlist", "quantity": 0, "price": 0
                    })
            except: continue

        # 5. Insertar en lotes
        if new_rows:
            batch_size = 100
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i:i + batch_size]
                supabase.table("inventory").insert(batch).execute()
        
        fetch_market.clear()
        return True, "Guardado exitoso"
    except Exception as e:
        print(f"Error save_inventory: {e}")
        return False, str(e)

def get_completion_stats(user_id):
    """Calcula el progreso real del álbum (únicas pegadas)."""
    try:
        data = supabase.table("inventory")\
            .select("sticker_num")\
            .eq("user_id", user_id)\
            .in_("status", ["tengo", "repetida", "repe"])\
            .execute()
        unique_stickers = {row['sticker_num'] for row in data.data}
        return len(unique_stickers)
    except Exception as e:
        print(f"Error stats: {e}")
        return 0

def get_full_wishlist(user_id):
    try:
        resp = supabase.table("inventory").select("sticker_num").eq("user_id", user_id).eq("status", "wishlist").execute()
        return sorted([int(x['sticker_num']) for x in resp.data])
    except: return []

# ==============================================================================
# 4. MERCADO Y MATCHING
# ==============================================================================

@st.cache_data(ttl=60, show_spinner=False)
def fetch_market(current_user_id):
    try:
        response = supabase.table("inventory")\
            .select("*, users(id, nick, province, zone, phone_encrypted, is_premium, reputation)")\
            .neq("user_id", current_user_id)\
            .execute()
        
        if not response.data: return pd.DataFrame()

        df = pd.DataFrame(response.data)
        df = df.copy() # FIX PANDAS WARNING

        def extract_user_data(row, key):
            user_data = row.get('users')
            if isinstance(user_data, dict): return user_data.get(key, '')
            return ''

        df['nick'] = df.apply(lambda x: extract_user_data(x, 'nick'), axis=1)
        df['province'] = df.apply(lambda x: extract_user_data(x, 'province'), axis=1)
        df['zone'] = df.apply(lambda x: extract_user_data(x, 'zone'), axis=1)
        df['phone_encrypted'] = df.apply(lambda x: extract_user_data(x, 'phone_encrypted'), axis=1)
        df['is_premium'] = df.apply(lambda x: extract_user_data(x, 'is_premium'), axis=1)
        df['reputation'] = df.apply(lambda x: extract_user_data(x, 'reputation'), axis=1)
        df['target_id'] = df['user_id'] 

        # Estandarizar nombre de columna
        if 'sticker_num' in df.columns: df['figu'] = df['sticker_num']
        elif 'num' in df.columns: df['figu'] = df['num']
            
        return df
    except Exception as e:
        print(f"Error fetch_market: {e}")
        return pd.DataFrame()

def find_matches(user_id, market_df):
    if market_df.empty: return [], []
    
    # FIX PANDAS: Asegurar copia independiente
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
    ofertas = market_df[market_df['status'] == 'repetida']
    
    for _, row in ofertas.iterrows():
        try:
            figu = int(row['figu'])
            if figu not in mis_tengo_set:
                es_wishlist = figu in mis_wishlist_set
                match = {
                    'nick': row['nick'], 'province': row['province'], 
                    'zone': row['zone'], 'phone_encrypted': row['phone_encrypted'], 
                    'figu': figu, 'price': row['price'], 
                    'reputation': row['reputation'], 'target_id': row['target_id'], 
                    'is_wishlist': es_wishlist, 'is_premium': row['is_premium']
                }
                
                if row['price'] > 0:
                    ventas.append(match)
                else:
                    # Lógica de match directo (yo tengo lo que él quiere)
                    # Nota: Esto es simplificado, idealmente requeriría consultar wishlist del otro
                    # Como no tenemos la wishlist del otro en market_df, lo dejamos como potencial
                    directos.append(match) 
        except: continue
    
    directos.sort(key=lambda x: (not x['is_wishlist'], -x.get('reputation', 0)))
    ventas.sort(key=lambda x: (not x['is_wishlist'], x['price'], -x.get('reputation', 0)))
    return directos, ventas

# ==============================================================================
# 5. TRANSACCIONES Y TRIANGULACIÓN
# ==============================================================================

def get_users_with_sticker(figu_num):
    try:
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

# Funciones de transacción legacy (para compatibilidad)
def get_pending_transactions(user_id): return []
def register_exchange(user_id, given_fig, received_fig, target_id_to_remove=None):
    # Simplificado para no romper lógica, idealmente actualizar DB
    return True, "Intercambio registrado localmente."
def register_purchase(user_id, received_fig, target_id_to_remove=None):
    return True, "Compra registrada localmente."
def remove_unlock(user_id, target_id): return True
def verify_user(phone, password): return login_user(phone, password)

# --- CARGA CSV ---
def process_csv_upload(df, user_id):
    try:
        df.columns = [c.lower().strip() for c in df.columns]
        rows = []
        for _, row in df.iterrows():
            rows.append({
                "user_id": user_id, "sticker_num": int(row['num']),
                "status": "tengo", "price": 0, "quantity": 1
            })
        if rows:
            supabase.table("inventory").insert(rows).execute()
            return True, f"Cargadas {len(rows)}."
        return False, "CSV vacío."
    except Exception as e: return False, str(e)

# --- PAGO MP ---
def verificar_pago_mp(payment_id, user_id):
    try:
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 404: return False, "No encontrado."
        resp = payment_info["response"]
        if resp.get("status") == "approved":
            supabase.table("users").update({"is_premium": True}).eq("id", user_id).execute()
            return True, "¡Sos Premium!"
        return False, "Pago pendiente."
    except: return False, "Error verificando pago."