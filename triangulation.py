import pandas as pd
import database as db
import streamlit as st

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    VERSIÓN DEBUG ROBUSTA (V2):
    Realiza consultas separadas para evitar errores de Foreign Key en Supabase.
    """
    st.markdown("### 🕵️‍♂️ Iniciando Diagnóstico de Triangulación (Modo Seguro)")
    
    # 1. Verificar mis datos
    st.write(f"**YO:** ID {user['id']} | Zona: '{user['zone']}' | Prov: '{user['province']}'")
    st.write(f"**BUSCO:** #{figu_objetivo}")
    
    # Chequeo de mis repetidas
    if 146 in mis_repes_ids:
        st.success(f"✅ Tu inventario ofrece la #146 correctamente. (IDs: {mis_repes_ids})")
    else:
        st.error(f"❌ TU INVENTARIO NO TIENE LA #146 CARGADA COMO REPE. Revisá la carga.")

    # ---------------------------------------------------------
    # 2. Análisis del TARGET (El que tiene la figu que quiero)
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown(f"#### 🔎 Buscando candidatos para la #{figu_objetivo}...")
    
    # PASO A: Consultar SOLO el inventario (sin JOIN a users para que no explote)
    try:
        inv_response = db.supabase.table("inventory").select("user_id, status").eq("num", figu_objetivo).execute()
        rows = inv_response.data
    except Exception as e:
        st.error(f"Error leyendo inventario: {e}")
        return []

    if not rows:
        st.error(f"❌ La base de datos dice que NADIE tiene la #{figu_objetivo}.")
        return []

    # Recolectamos los IDs de los usuarios que la tienen
    user_ids_found = [r['user_id'] for r in rows]
    st.write(f"📊 Registros encontrados en inventario: {len(rows)} (IDs: {user_ids_found})")

    # PASO B: Consultar los detalles de esos usuarios
    if user_ids_found:
        users_response = db.supabase.table("users").select("id, nick, province, zone").in_("id", user_ids_found).execute()
        users_map = {u['id']: u for u in users_response.data}
    else:
        users_map = {}

    # PASO C: Cruzar datos y validar
    candidatos_validos = []
    
    for row in rows:
        uid = row['user_id']
        raw_status = str(row.get('status', '')).lower().strip()
        
        # Obtenemos datos del usuario del mapa
        user_data = users_map.get(uid)
        
        st.markdown(f"👉 **Analizando ID {uid}:**")
        st.write(f"   - Status en DB: **'{row.get('status')}'**")
        
        if not user_data:
            st.error(f"   ❌ El usuario ID {uid} tiene la figurita pero NO existe en la tabla `users`.")
            continue
            
        u_prov = str(user_data.get('province', '')).strip()
        u_zone = str(user_data.get('zone', '')).strip()
        st.write(f"   - Ubicación: '{u_prov}' - '{u_zone}'")

        # Validaciones
        # 1. Status (debe ser repetida)
        status_ok = raw_status in ['repetida', 'repe']
        if not status_ok:
            st.warning(f"   ⚠️ Status inválido. Es '{raw_status}', se necesita 'repetida'.")
        
        # 2. Zona (debe coincidir con la tuya)
        my_prov = str(user['province']).strip()
        my_zone = str(user['zone']).strip()
        zone_ok = (u_prov == my_prov) and (u_zone == my_zone)
        
        if not zone_ok:
            st.warning(f"   ⚠️ Zona distinta. (El: {u_zone} vs Vos: {my_zone})")

        if status_ok and zone_ok:
            st.success("   ✅ ¡Candidato Válido!")
            candidatos_validos.append(uid)

    if not candidatos_validos:
        st.error("🛑 No hay Targets válidos. Fin del análisis.")
        return []

    # ---------------------------------------------------------
    # 3. Análisis del PUENTE (Si llegamos acá)
    # ---------------------------------------------------------
    # Aca el código original hubiera buscado wishlists.
    # Para el diagnóstico, solo mostramos si los Targets quieren algo.
    st.markdown("---")
    st.markdown("#### 🌉 Análisis de Wishlists (Targets)")
    
    w_response = db.supabase.table("inventory").select("user_id, num").in_("user_id", candidatos_validos).eq("status", "wishlist").execute()
    
    deseos_targets = [r['num'] for r in w_response.data]
    st.write(f"Los Targets quieren estas figuritas: {deseos_targets}")
    
    if 166 in deseos_targets: # 166 es la que tiene el Puente
        st.success("✅ ¡Uno de los targets quiere la #166! (Paso correcto)")
    else:
        st.error("❌ Ningún Target marcó la #166 en su wishlist.")

    return [] # Cortamos para leer el reporte