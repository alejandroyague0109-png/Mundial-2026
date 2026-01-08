import streamlit as st
import pandas as pd
import database as db
import utils

def marcar_cambio():
    st.session_state.unsaved_changes = True

def render_inventory(user, start, end, country_name):
    # 1. Init bandera cambios
    if 'unsaved_changes' not in st.session_state: st.session_state.unsaved_changes = False

    # 2. Carga Inicial de Datos (Solo si no están en memoria)
    session_key = f"inv_state_{country_name}"
    if session_key not in st.session_state:
        db_tengo, db_wishlist, db_repes_info, _ = db.get_inventory_status(user['id'], start, end)
        repes_rows = []
        for num, info in db_repes_info.items():
            modo = "Venta" if info['price'] > 0 else "Canje"
            repes_rows.append({"Figurita": num, "Modo": modo, "Precio": info['price'], "Cantidad": info['quantity']})
            
        st.session_state[session_key] = {'owned': db_tengo, 'wishlist': db_wishlist, 'repes': repes_rows}
        st.session_state.unsaved_changes = False

    # Alias
    state = st.session_state[session_key]
    numeros_pagina = list(range(start, end + 1))

    # --- ENCABEZADO Y GUARDAR ---
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"{country_name} ({start}-{end})")
    
    btn_type = "primary" if st.session_state.unsaved_changes else "secondary"
    btn_text = "💾 Guardar Cambios (*)" if st.session_state.unsaved_changes else "💾 Guardar Cambios"
    
    if c2.button(btn_text, type=btn_type, use_container_width=True):
        with utils.spinner_futbolero():
            df_repes_tosave = pd.DataFrame(state['repes'])
            db.save_inventory_positive(user['id'], start, end, state['owned'], state['wishlist'], df_repes_tosave)
            st.session_state.unsaved_changes = False
        st.toast("¡Álbum actualizado!", icon="✅"); st.rerun()

    st.markdown("---")

    # --- SECCIÓN 1: TENGO ---
    st.markdown("### ✅ ¿Cuáles Tenés?")
    
    # Lógica corregida para "Seleccionar Todas" / "Borrar Todas"
    key_tengo = f"pills_tengo_{country_name}"
    
    col_sel1, col_sel2, _ = st.columns([1, 1, 3])
    
    if col_sel1.button("Seleccionar Todas"):
        state['owned'] = list(numeros_pagina)
        state['wishlist'] = [] 
        st.session_state[key_tengo] = list(numeros_pagina) # Forzar actualización visual
        marcar_cambio()
        st.rerun()
        
    if col_sel2.button("Borrar Todas"):
        state['owned'] = []
        state['repes'] = []
        st.session_state[key_tengo] = [] # Forzar actualización visual
        marcar_cambio()
        st.rerun()

    seleccion_tengo = st.pills(
        "Seleccioná las que tenés",
        options=numeros_pagina,
        default=state['owned'],
        selection_mode="multi",
        key=key_tengo,
        on_change=marcar_cambio
    )
    
    # Actualizar lógica
    state['owned'] = seleccion_tengo
    state['wishlist'] = [x for x in state['wishlist'] if x not in state['owned']]

    st.markdown("---")

    # --- SECCIÓN 2: WISHLIST ---
    st.markdown("### ❤️ ¿Cuáles Buscás?")
    opciones_wishlist = [n for n in numeros_pagina if n not in state['owned']]
    current_wishlist_clean = [n for n in state['wishlist'] if n in opciones_wishlist]
    
    seleccion_wishlist = st.pills(
        "Seleccioná tus faltantes",
        options=opciones_wishlist,
        default=current_wishlist_clean,
        selection_mode="multi",
        key=f"pills_wish_{country_name}",
        on_change=marcar_cambio
    )
    state['wishlist'] = seleccion_wishlist

    st.markdown("---")
    
    # --- SECCIÓN 3: REPETIDAS (AHORA CON PILLS) ---
    st.markdown("### 🔁 Mis Repetidas")
    
    posibles_repes = sorted(state['owned'])
    
    if not posibles_repes:
        st.info("👆 Primero marcá figuritas en '¿Cuáles Tenés?' para poder cargar repetidas.")
        state['repes'] = [] # Limpiar si no hay owned
    else:
        st.caption("Tocá las casillas de las que tengas repetidas:")
        
        # 1. SELECTOR TIPO PILLS (CASILLAS)
        repes_actuales_nums = [r['Figurita'] for r in state['repes'] if r['Figurita'] in posibles_repes]
        
        seleccion_repes = st.pills(
            "Seleccioná repetidas",
            options=posibles_repes,
            default=repes_actuales_nums,
            selection_mode="multi",
            key=f"pills_repes_{country_name}",
            on_change=marcar_cambio
        )
        
        # 2. CONSTRUCCIÓN DATA TABLE
        new_repes_data = []
        for num in seleccion_repes:
            existing_data = next((r for r in state['repes'] if r['Figurita'] == num), None)
            if existing_data:
                new_repes_data.append(existing_data)
            else:
                new_repes_data.append({"Figurita": num, "Modo": "Canje", "Precio": 0, "Cantidad": 1})
        
        state['repes'] = new_repes_data
        
        # 3. TABLA DE EDICIÓN
        if state['repes']:
            df_repes = pd.DataFrame(state['repes'])
            
            column_config = {
                "Figurita": st.column_config.NumberColumn("Número", disabled=True),
                "Modo": st.column_config.SelectboxColumn("Objetivo", options=["Canje", "Venta"], required=True, default="Canje"),
                "Precio": st.column_config.NumberColumn("Precio ($)", min_value=0, step=100, default=0),
                "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1, step=1, default=1)
            }
            
            edited_df = st.data_editor(
                df_repes, 
                num_rows="fixed", 
                column_config=column_config, 
                use_container_width=True, 
                hide_index=True,
                key=f"editor_{country_name}",
                on_change=marcar_cambio
            )
            
            if not edited_df.equals(pd.DataFrame(state['repes'])):
                state['repes'] = edited_df.to_dict('records')