import streamlit as st
import pandas as pd
import time
import database as db
import utils # <--- Importamos utils

def render_inventory(user, start, end, seleccion_pais):
    st.header("📖 Mi Álbum")
    
    # Spinner al cargar tus figus
    # Nota: No cacheamos esto porque queremos ver cambios instantáneos,
    # pero es tan rápido que quizás ni se vea el spinner.
    ids_tengo_db, repetidas_info, _ = db.get_inventory_status(user['id'], start, end)
    key_pills = f"pills_tengo_{seleccion_pais}"

    if key_pills not in st.session_state:
        st.session_state[key_pills] = ids_tengo_db

    col_head_1, col_btn_all, col_btn_none = st.columns([4, 1, 1])
    col_head_1.markdown("### 1️⃣ Tus Figus")

    if col_btn_all.button("Todas", use_container_width=True, key=f"all_{seleccion_pais}"):
        st.session_state[key_pills] = list(range(start, end + 1))
        st.rerun()

    if col_btn_none.button("Ninguna", use_container_width=True, key=f"none_{seleccion_pais}"):
        st.session_state[key_pills] = []
        st.rerun()

    seleccion_tengo = st.pills("Tengo", list(range(start, end + 1)), selection_mode="multi", key=key_pills, label_visibility="collapsed")

    st.markdown("### 2️⃣ Repes")
    posibles_repes = sorted(seleccion_tengo) if seleccion_tengo else []
    ids_repes_val = [k for k in repetidas_info.keys() if k in posibles_repes]
    seleccion_repes = st.pills("Repes", posibles_repes, default=ids_repes_val, selection_mode="multi", key=f"repes_{seleccion_pais}")

    if seleccion_repes:
        st.info("👇 **Data:** Hacé doble clic en 'Modo' para cambiar entre **Canje** y **Venta**. Ajustá la 'Cantidad'.")
        data = []
        for n in seleccion_repes:
            info = repetidas_info.get(n, {})
            precio = info.get('price', 0)
            qty = info.get('quantity', 1)
            modo = "💰 Venta" if precio > 0 else "🔄 Canje"
            data.append({"Figurita": n, "Cantidad": qty, "Modo": modo, "Precio": precio})
            
        edited_df = st.data_editor(
            pd.DataFrame(data), 
            column_config={
                "Figurita": st.column_config.NumberColumn(disabled=True),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1, help="Copias disponibles"),
                "Modo": st.column_config.SelectboxColumn(options=["🔄 Canje", "💰 Venta"], required=True),
                "Precio": st.column_config.NumberColumn(min_value=0, step=100)
            }, 
            hide_index=True, use_container_width=True
        )
        
        if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
            # AQUI ESTA EL FEEDBACK VISUAL
            with utils.spinner_futbolero():
                db.save_inventory_positive(user['id'], start, end, seleccion_tengo, edited_df)
            
            st.toast("Joyas guardadas", icon="💾")
            time.sleep(0.5)
            st.rerun()