import streamlit as st
import pandas as pd
import time
import database as db
import utils 

# --- FUNCIÓN AUXILIAR PARA DETECTAR CAMBIOS ---
def marcar_cambio():
    st.session_state.unsaved_changes = True

def render_inventory(user, start, end, seleccion_pais):
    # Desempaquetamos 4 valores
    ids_tengo_db, ids_wishlist_db, repetidas_info, _ = db.get_inventory_status(user['id'], start, end)
    
    # Definimos las claves para la Session State
    key_pills = f"pills_tengo_{seleccion_pais}"
    key_wish = f"pills_wish_{seleccion_pais}"
    key_repes = f"repes_{seleccion_pais}" 

    # --- 1. INICIALIZACIÓN DE ESTADO ---
    if key_pills not in st.session_state: st.session_state[key_pills] = ids_tengo_db
    if key_wish not in st.session_state: st.session_state[key_wish] = ids_wishlist_db
    
    # --- ENCABEZADO Y BOTONES MASIVOS ---
    col_head_1, col_btn_all, col_btn_none = st.columns([4, 1, 1])
    col_head_1.markdown("### 1️⃣ Tus Figus")

    # Botones masivos (Marcan cambio explícitamente)
    if col_btn_all.button("Todas", width="stretch", key=f"all_{seleccion_pais}"):
        st.session_state[key_pills] = list(range(start, end + 1))
        st.session_state[key_wish] = [] 
        st.session_state.unsaved_changes = True # <--- CAMBIO
        st.rerun()

    if col_btn_none.button("Ninguna", width="stretch", key=f"none_{seleccion_pais}"):
        st.session_state[key_pills] = []
        st.session_state.unsaved_changes = True # <--- CAMBIO
        st.rerun()

    # --- WIDGET TENGO (Con on_change) ---
    seleccion_tengo = st.pills(
        "Tengo", 
        list(range(start, end + 1)), 
        selection_mode="multi", 
        key=key_pills, 
        label_visibility="collapsed",
        on_change=marcar_cambio # <--- DETECTOR
    )

    # --- SECCIÓN WISHLIST ---
    st.markdown("### ❤️ Wishlist (Prioridad)")
    st.caption("Marcá las que **TE FALTAN** y querés conseguir urgente.")
    
    todas = set(range(start, end + 1))
    tengo_set = set(seleccion_tengo) if seleccion_tengo else set()
    faltantes = sorted(list(todas - tengo_set))
    
    current_wish = st.session_state.get(key_wish, [])
    clean_wish = [x for x in current_wish if x in faltantes]
    st.session_state[key_wish] = clean_wish
    
    # Widget Wishlist (Con on_change)
    seleccion_wishlist = st.pills(
        "Deseo", 
        faltantes, 
        selection_mode="multi", 
        key=key_wish,
        on_change=marcar_cambio # <--- DETECTOR
    )

    # --- SECCIÓN REPETIDAS ---
    st.markdown("### 2️⃣ Repes")
    
    posibles_repes = sorted(seleccion_tengo) if seleccion_tengo else []
    
    if key_repes not in st.session_state:
        ids_repes_val = [k for k in repetidas_info.keys() if k in posibles_repes]
        st.session_state[key_repes] = ids_repes_val
    else:
        current_repes = st.session_state[key_repes]
        valid_repes = [x for x in current_repes if x in posibles_repes]
        st.session_state[key_repes] = valid_repes

    # Widget Repes (Con on_change)
    seleccion_repes = st.pills(
        "Repes", 
        posibles_repes, 
        selection_mode="multi", 
        key=key_repes,
        on_change=marcar_cambio # <--- DETECTOR
    )

    # --- EDITOR DE DATOS ---
    edited_df = pd.DataFrame()
    if seleccion_repes:
        st.info("👇 **Data:** Hacé doble clic en 'Modo' para cambiar entre **Canje** y **Venta**.")
        data = []
        for n in seleccion_repes:
            info = repetidas_info.get(n, {})
            # Si ya se editó algo en la sesión, usamos eso, sino la DB
            # (Nota: Streamlit maneja el estado del editor internamente, pero el on_change nos avisa)
            precio = info.get('price', 0)
            qty = info.get('quantity', 1)
            modo = "💰 Venta" if precio > 0 else "🔄 Canje"
            data.append({"Figurita": n, "Cantidad": qty, "Modo": modo, "Precio": precio})
            
        edited_df = st.data_editor(
            pd.DataFrame(data), 
            column_config={
                "Figurita": st.column_config.NumberColumn(disabled=True),
                "Cantidad": st.column_config.NumberColumn(min_value=1, step=1),
                "Modo": st.column_config.SelectboxColumn(options=["🔄 Canje", "💰 Venta"], required=True),
                "Precio": st.column_config.NumberColumn(min_value=0, step=100)
            }, 
            hide_index=True, 
            use_container_width=True,
            on_change=marcar_cambio # <--- DETECTOR
        )
    
    st.divider()

    # --- BOTÓN GUARDAR (Cambia color si hay cambios) ---
    btn_type = "primary" if st.session_state.get('unsaved_changes', False) else "secondary"
    btn_lbl = "💾 GUARDAR CAMBIOS (*)" if st.session_state.get('unsaved_changes', False) else "💾 GUARDAR CAMBIOS"

    if st.button(btn_lbl, type=btn_type, width="stretch"):
        with utils.spinner_futbolero():
            db.save_inventory_positive(user['id'], start, end, seleccion_tengo, seleccion_wishlist, edited_df)
            st.session_state.unsaved_changes = False # <--- RESETEAMOS LA BANDERA
        
        st.toast("¡Cambios guardados!", icon="✅")
        time.sleep(0.5)
        st.rerun()