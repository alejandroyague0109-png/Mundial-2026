import streamlit as st
import pandas as pd
import database as db
import utils
import config
import time

def render_admin_panel(admin_user):
    st.title("🛡️ Panel de Control - Director Técnico")
    st.info(f"Sesión iniciada como: {admin_user['nick']} (Admin)")

    # --- 1. DATA FETCHING (EXTRACCIÓN DE DATOS) ---
    # Traemos datos crudos para procesar métricas en Python (seguro para MVP)
    try:
        # Usuarios
        res_users = db.supabase.table("users").select("*").execute()
        df_users = pd.DataFrame(res_users.data)
        
        # Transacciones
        res_req = db.supabase.table("transaction_requests").select("*").execute()
        df_req = pd.DataFrame(res_req.data)
        
        # Inventario (Solo conteo rápido para no saturar)
        count_tengo = db.supabase.table("inventory").select("id", count="exact").eq("status", "tengo").execute().count
        count_wish = db.supabase.table("inventory").select("id", count="exact").eq("status", "wishlist").execute().count
        
    except Exception as e:
        st.error(f"Error conectando a DB: {e}")
        return

    # --- 2. KPI DASHBOARD (MÉTRICAS CLAVE) ---
    st.markdown("### 📊 Indicadores Principales")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    total_users = len(df_users)
    total_premium = len(df_users[df_users['is_premium'] == True])
    revenue_est = total_premium * config.PRECIO_PREMIUM # Estimación simple
    tasa_conversion = round((total_premium / total_users * 100), 2) if total_users > 0 else 0

    kpi1.metric("Usuarios Totales", total_users, delta=f"{len(df_users[df_users['reputation'] > 0])} activos")
    kpi2.metric("Usuarios Premium", total_premium, delta=f"{tasa_conversion}% conv.")
    kpi3.metric("Ingresos Estimados", f"${revenue_est:,.0f}", help="Total histórico acumulado")
    kpi4.metric("Figuritas en el Mercado", count_tengo, delta=f"Demanda: {count_wish}")

    st.divider()

    # --- 3. PESTAÑAS DE GESTIÓN ---
    tab_analytics, tab_users, tab_db = st.tabs(["📈 Analítica", "👥 Gestión Usuarios", "🔧 Mantenimiento"])

    # --- TAB ANALÍTICA ---
    with tab_analytics:
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("🗺️ Mapa de Calor (Provincias)")
            if not df_users.empty and 'province' in df_users.columns:
                prov_counts = df_users['province'].value_counts()
                st.bar_chart(prov_counts, color="#2e7d32") # Verde cancha
            else:
                st.info("Faltan datos geográficos.")

        with c2:
            st.subheader("⚖️ Oferta vs Demanda")
            # Gráfico simple de torta simulado con dataframe
            data_market = pd.DataFrame({
                'Tipo': ['Oferta (Tengo)', 'Demanda (Busco)'],
                'Cantidad': [count_tengo, count_wish]
            }).set_index('Tipo')
            st.bar_chart(data_market, horizontal=True)
            
            st.subheader("🏆 Top Traders (Reputación)")
            if not df_users.empty:
                top_users = df_users.sort_values(by='reputation', ascending=False).head(5)
                st.dataframe(
                    top_users[['nick', 'reputation', 'province', 'is_premium']], 
                    hide_index=True, 
                    use_container_width=True
                )

    # --- TAB GESTIÓN USUARIOS ---
    with tab_users:
        st.subheader("Buscador de Usuarios")
        search = st.text_input("Buscar por Nick, Zona o ID", placeholder="Escribí algo...")
        
        if search and not df_users.empty:
            # Filtro local en pandas (más rápido para admins)
            mask = df_users.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            results = df_users[mask]
            
            if not results.empty:
                st.dataframe(
                    results[['id', 'nick', 'province', 'daily_contacts_count', 'is_premium', 'reputation']],
                    use_container_width=True
                )
                
                target_id = st.selectbox("Seleccionar ID para editar", results['id'].tolist())
                
                # Acciones sobre el usuario seleccionado
                st.markdown(f"**Acciones para ID: {target_id}**")
                ac1, ac2, ac3, ac4 = st.columns(4)
                
                if ac1.button("💎 Dar Premium"):
                    db.supabase.table("users").update({"is_premium": True}).eq("id", target_id).execute()
                    st.toast("Usuario actualizado a Premium", icon="💎")
                    time.sleep(1); st.rerun()
                
                if ac2.button("🚫 Quitar Premium"):
                    db.supabase.table("users").update({"is_premium": False}).eq("id", target_id).execute()
                    st.toast("Premium removido", icon="⬇️")
                    time.sleep(1); st.rerun()
                    
                if ac3.button("🎁 Resetear Límite Diario"):
                    db.supabase.table("users").update({"daily_contacts_count": 0}).eq("id", target_id).execute()
                    st.toast("Contador reseteado", icon="🔄")
                
                if ac4.button("👮 Hacer Admin"):
                    db.supabase.table("users").update({"is_admin": True}).eq("id", target_id).execute()
                    st.warning("¡Nuevo Admin designado!")

            else:
                st.warning("No se encontraron usuarios.")
        else:
            st.info("Utilizá el buscador para gestionar permisos.")

    # --- TAB MANTENIMIENTO ---
    with tab_db:
        st.subheader("Herramientas de Mantenimiento")
        
        col_m1, col_m2 = st.columns(2)
        
        with col_m1:
            st.markdown("### 📅 Ciclo Diario")
            if st.button("🔄 Resetear Límites Diarios (GLOBAL)", type="primary"):
                with utils.spinner_futbolero():
                    db.supabase.table("users").update({"daily_contacts_count": 0}).neq("id", 0).execute()
                st.success("¡Todos los usuarios tienen 0 créditos usados ahora!")
        
        with col_m2:
            st.markdown("### 🧹 Limpieza")
            st.caption("Elimina solicitudes de canje rechazadas o canceladas para ahorrar espacio.")
            if st.button("🗑️ Limpiar Solicitudes Viejas"):
                # Borramos solo las que NO están pendientes ('pending')
                try:
                    db.supabase.table("transaction_requests").delete().neq("status", "pending").execute()
                    st.success("Se limpió el historial de transacciones finalizadas/canceladas.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        with st.expander("🚨 ZONA DE PELIGRO (SOLO DESARROLLO)"):
            st.warning("Estas acciones son destructivas.")
            if st.button("🔥 Borrar TODAS las Transacciones (Reset Mercado)"):
                db.supabase.table("transaction_requests").delete().neq("id", 0).execute()
                st.error("Tabla de transacciones vaciada.")