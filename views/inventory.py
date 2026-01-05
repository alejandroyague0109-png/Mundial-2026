import streamlit as st
import pandas as pd
import time
import database as db
import utils 

def render_inventory(user, start, end, seleccion_pais):
    # Desempaquetamos 4 valores
    ids_tengo_db, ids_wishlist_db, repetidas_info, _ = db.get_inventory_status(user['id'], start, end)
    
    # Definimos las claves para la Session State
    key_pills = f"pills_tengo_{seleccion_pais}"
    key_wish = f"pills_wish_{seleccion_pais}"
    key_repes = f"repes_{seleccion_pais}" # Clave para repes

    # --- 1. INICIALIZACIÓN DE ESTADO (Solo si no existen) ---
    if key_pills not in st.session_state: st.session_state[key_pills] = ids_tengo_db
    if key_wish not in st.session_state: st.session_state[key_wish] = ids_wishlist_db
    
    # --- ENCABEZADO Y BOTONES MASIVOS ---
    col_head_1, col_btn_all, col_btn_none = st.columns([4, 1, 1])
    col_head_1.markdown("### 1️⃣ Tus Figus")

    if col_btn_all.button("Todas", width="stretch", key=f"all_{seleccion_pais}"):
        st.session_state[key_pills] = list(range(start, end + 1))
        st.session_state[key_wish] = [] # Si tengo todas, borro wishlist
        st.rerun()

    if col_btn_none.button("Ninguna", width="stretch", key=f"none_{seleccion_pais}"):
        st.session_state[key_pills] = []
        st.rerun()

    # --- WIDGET TENGO ---
    # Nota: Aquí no usábamos default, así que estaba bien.
    seleccion_tengo = st.pills("Tengo", list(range(start, end + 1)), selection_mode="multi", key=key_pills, label_visibility="collapsed")

    # --- SECCIÓN WISHLIST (CORREGIDA) ---
    st.markdown("### ❤️ Wishlist (Prioridad)")
    st.caption("Marcá las que **TE FALTAN** y querés conseguir urgente. Te aparecerán primero en el mercado.")
    
    # Calculamos qué figuritas faltan (Universo - Tengo)
    todas = set(range(start, end + 1))
    tengo_set = set(seleccion_tengo) if seleccion_tengo else set()
    faltantes = sorted(list(todas - tengo_set))
    
    # LÓGICA DE CORRECCIÓN:
    # 1. Obtenemos lo que hay en memoria actualmente para la wishlist
    current_wish = st.session_state.get(key_wish, [])
    # 2. "Sanitizamos": Solo mantenemos en la wishlist las que realmente me faltan.
    #    (Si marqué una como "Tengo", debe salir de la wishlist automáticamente).
    clean_wish = [x for x in current_wish if x in faltantes]
    # 3. Actualizamos la memoria ANTES de crear el widget
    st.session_state[key_wish] = clean_wish
    
    # 4. Creamos el widget SIN 'default', leyendo directo de la key
    seleccion_wishlist = st.pills("Deseo", faltantes, selection_mode="multi", key=key_wish)

    # --- SECCIÓN REPETIDAS (CORREGIDA PROACTIVAMENTE) ---
    st.markdown("### 2️⃣ Repes")
    
    # Calculamos cuáles pueden ser repetidas (tienen que estar en "Tengo")
    posibles_repes = sorted(seleccion_tengo) if seleccion_tengo else []
    
    # Si la clave de repes no existe o necesitamos reinicializarla basada en la DB la primera vez
    # Pero como 'repes' depende dinámicamente de 'tengo', hacemos una validación:
    
    # 1. Recuperamos valores actuales de la UI o inicializamos con DB si es la primera vez
    if key_repes not in st.session_state:
        # Primera vez: Usamos lo que vino de la base de datos
        ids_repes_val = [k for k in repetidas_info.keys() if k in posibles_repes]
        st.session_state[key_repes] = ids_repes_val
    else:
        # Ya existe: Aseguramos que lo seleccionado sea válido (que siga estando en 'posibles_repes')
        current_repes = st.session_state[key_repes]
        valid_repes = [x for x in current_repes if x in posibles_repes]
        st.session_state[key_repes] = valid_repes

    # 2. Creamos el widget SIN 'default'
    seleccion_repes = st.pills("Repes", posibles_repes, selection_mode="multi", key=key_repes)

    # --- EDITOR DE DATOS ---
    edited_df = pd.DataFrame()
    if seleccion_repes:
        st.info("👇 **Data:** Hacé doble clic en 'Modo' para cambiar entre **Canje** y **Venta**. Ajustá la 'Cantidad'.")
        data = []
        for n in seleccion_repes:
            # Intentamos recuperar info previa (memoria o DB)
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
    
    st.divider()

    # --- BOTÓN GUARDAR ---
    if st.button("💾 GUARDAR CAMBIOS", type="primary", width="stretch"):
        with utils.spinner_futbolero():
            # Pasamos TAMBIÉN la wishlist al guardar
            db.save_inventory_positive(user['id'], start, end, seleccion_tengo, seleccion_wishlist, edited_df)
        
        st.toast("Joyas guardadas (y wishlist actualizada)", icon="💾")
        time.sleep(0.5)
        st.rerun()