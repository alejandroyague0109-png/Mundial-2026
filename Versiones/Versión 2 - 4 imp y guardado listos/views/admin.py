import streamlit as st
import pandas as pd
import database as db
import utils
import time

def render_admin_panel(admin_user):
    st.title("🛡️ Panel de Administrador")
    st.info(f"Sesión iniciada como: {admin_user['nick']} (Admin)")

    # --- KPI DASHBOARD ---
    col1, col2, col3 = st.columns(3)
    
    # Consultas rápidas para KPIs (Simuladas o reales según DB)
    try:
        users_count = len(db.supabase.table("users").select("id", count="exact").execute().data)
        inv_count = len(db.supabase.table("inventory").select("id", count="exact").execute().data)
        req_count = len(db.supabase.table("transaction_requests").select("id", count="exact").execute().data)
    except:
        users_count, inv_count, req_count = 0, 0, 0

    col1.metric("Usuarios", users_count)
    col2.metric("Figuritas Cargadas", inv_count)
    col3.metric("Transacciones", req_count)

    st.divider()

    # --- PESTAÑAS DE GESTIÓN ---
    tab_users, tab_db = st.tabs(["👥 Gestión Usuarios", "🔧 Base de Datos"])

    with tab_users:
        st.subheader("Buscar Usuario")
        search = st.text_input("Buscar por Nick o Teléfono (hash/encriptado)", placeholder="Escribí algo...")
        
        if search:
            # Búsqueda simple en Supabase
            res = db.supabase.table("users").select("*").ilike("nick", f"%{search}%").execute()
            df_users = pd.DataFrame(res.data)
            
            if not df_users.empty:
                st.dataframe(df_users[['id', 'nick', 'province', 'reputation', 'is_premium', 'is_admin']])
                
                target_id = st.selectbox("Seleccionar ID para acciones", df_users['id'].tolist())
                
                c1, c2, c3 = st.columns(3)
                if c1.button("💎 Dar Premium"):
                    db.supabase.table("users").update({"is_premium": True}).eq("id", target_id).execute()
                    st.success("¡Usuario ahora es Premium!")
                
                if c2.button("🚫 Quitar Premium"):
                    db.supabase.table("users").update({"is_premium": False}).eq("id", target_id).execute()
                    st.warning("Premium removido.")
                    
                if c3.button("👮 Hacer Admin"):
                    db.supabase.table("users").update({"is_admin": True}).eq("id", target_id).execute()
                    st.error("¡Usuario ahora es ADMIN!")

            else:
                st.warning("No se encontraron usuarios.")

    with tab_db:
        st.subheader("Herramientas de Mantenimiento")
        
        if st.button("🔄 Resetear Límites Diarios (Todos)", type="primary"):
            with utils.spinner_futbolero():
                db.supabase.table("users").update({"daily_contacts_count": 0}).neq("id", 0).execute()
            st.success("Se reiniciaron los contadores de todos los usuarios.")
            
        with st.expander("🗑️ ZONA DE PELIGRO"):
            st.warning("Acciones irreversibles")
            if st.button("🔥 Borrar TODAS las Transacciones Pendientes"):
                db.supabase.table("transaction_requests").delete().neq("id", 0).execute()
                st.error("Tabla limpiada.")