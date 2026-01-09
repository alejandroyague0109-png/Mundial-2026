import pandas as pd
import database as db
import streamlit as st

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    VERSIÓN DEBUG: Diagnóstico detallado en pantalla.
    """
    st.markdown("### 🕵️‍♂️ Iniciando Diagnóstico de Triangulación")
    
    # 1. Verificar mis datos
    st.write(f"**YO:** ID {user['id']} | Zona: '{user['zone']}' | Prov: '{user['province']}'")
    st.write(f"**BUSCO:** #{figu_objetivo}")
    st.write(f"**OFREZCO (Mis Repes IDs):** {mis_repes_ids}")
    
    if 146 in mis_repes_ids:
        st.success("✅ El sistema detecta que tenés la #146 para ofrecer.")
    else:
        st.error(f"❌ El sistema NO ve la #146 en tus repetidas. Revisa `get_inventory_status`.")

    # 2. Análisis del Target (Usuario 2 - Figu 176)
    st.markdown("---")
    st.markdown(f"#### 🔎 Buscando la #{figu_objetivo} en la DB...")
    
    # Consulta RAW para ver todo sin filtros
    response = db.supabase.table("inventory").select("user_id, status, users(nick, province, zone)").eq("num", figu_objetivo).execute()
    
    if not response.data:
        st.error(f"❌ No hay NINGÚN registro de la #{figu_objetivo} en la tabla inventory.")
        return []
        
    for row in response.data:
        uid = row['user_id']
        status = row['status']
        user_data = row.get('users')
        
        st.write(f"👉 Encontrada en usuario ID: **{uid}** | Status: **'{status}'**")
        
        if not user_data:
            st.error(f"   ❌ CRÍTICO: El usuario {uid} NO existe en la tabla `users` o la relación está rota.")
            continue
            
        u_prov = user_data.get('province')
        u_zone = user_data.get('zone')
        
        st.write(f"   📍 Ubicación: '{u_prov}' - '{u_zone}'")
        
        # Chequeos
        check_status = str(status).lower().strip() in ['repetida', 'repe']
        check_zone = (str(u_zone).strip() == str(user['zone']).strip())
        
        if check_status and check_zone:
            st.success(f"   ✅ Candidato Válido (Target)")
        else:
            st.warning(f"   ⚠️ Descartado: Status OK? {check_status} | Zona OK? {check_zone}")

    # 3. Análisis del Puente (Usuario 5 - Figu 166)
    # (Solo si pasamos la etapa anterior, pero mostramos lógica general)
    return [] # Cortamos aquí para que veas el reporte.