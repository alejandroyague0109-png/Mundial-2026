import streamlit as st
import pandas as pd
import database as db
import utils

# Función auxiliar para activar la bandera de "Cambios sin guardar"
def marcar_cambio():
    st.session_state.unsaved_changes = True

def render_inventory(user, start, end, country_name):
    # 1. Inicializar bandera de cambios
    if 'unsaved_changes' not in st.session_state:
        st.session_state.unsaved_changes = False

    # 2. Carga de datos (Solo si no están en memoria de sesión para este país)
    session_key = f"inv_state_{country_name}"
    
    if session_key not in st.session_state:
        # Traemos de la base de datos
        db_tengo, db_wishlist, db_repes_info, _ = db.get_inventory_status(user['id'], start, end)
        
        # Preparamos las repetidas para el editor
        repes_rows = []
        for num, info in db_repes_info.items():
            modo = "Venta" if info['price'] > 0 else "Canje"
            repes_rows.append({
                "Figurita": num,
                "Modo": modo,
                "Precio": info['price'],
                "Cantidad": info['quantity']
            })
            
        # Guardamos en Session State
        st.session_state[session_key] = {
            'owned': db_tengo,
            'wishlist': db_wishlist,
            'repes': repes_rows 
        }
        st.session_state.unsaved_changes = False

    # Alias para trabajar más cómodo
    state = st.session_state[session_key]

    # --- ENCABEZADO Y GUARDADO ---
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"{country_name} ({start}-{end})")
    
    # Botón Guardar (Cambia de color si hay cambios pendientes)
    btn_type = "primary" if st.session_state.unsaved_changes else "secondary"
    btn_text = "💾 Guardar Cambios (*)" if st.session_state.unsaved_changes else "💾 Guardar Cambios"
    
    if c2.button(btn_text, type=btn_type, use_container_width=True):
        with utils.spinner_futbolero():
            df_repes_tosave = pd.DataFrame(state['repes'])
            # Guardamos Owned, Wishlist y Repes
            db.save_inventory_positive(user['id'], start, end, state['owned'], state['wishlist'], df_repes_tosave)
            st.session_state.unsaved_changes = False
        st.toast("¡Álbum actualizado!", icon="✅")
        st.rerun()

    st.markdown("---")

    # --- SECCIÓN 1: TENGO (Selección Múltiple) ---
    st.markdown("### ✅ ¿Cuáles Tenés?")
    st.caption("Tocá los números para marcarlos como 'Tengo'.")
    
    numeros_pagina = list(range(start, end + 1))
    
    # Widget de selección múltiple (Pills)
    seleccion_tengo = st.pills(
        "Seleccioná las que tenés",
        options=numeros_pagina,
        default=state['owned'],
        selection_mode="multi",
        key=f"pills_tengo_{country_name}",
        on_change=marcar_cambio
    )
    
    # Actualizamos el estado inmediatamente al cambiar
    state['owned'] = seleccion_tengo
    # Limpieza cruzada: Si marco que la tengo, la saco de wishlist automáticamente
    state['wishlist'] = [x for x in state['wishlist'] if x not in state['owned']]

    st.markdown("---")

    # --- SECCIÓN 2: WISHLIST (Selección Múltiple) ---
    st.markdown("### ❤️ ¿Cuáles Buscás? (Wishlist)")
    st.caption("Marcá las que te faltan. (Se deshabilitan las que ya marcaste arriba).")
    
    # Opcional: Filtramos visualmente las que ya tiene para no confundir
    opciones_wishlist = [n for n in numeros_pagina if n not in state['owned']]
    
    # Limpieza preventiva del default por si cambió 'owned'
    current_wishlist_clean = [n for n in state['wishlist'] if n in opciones_wishlist]
    
    seleccion_wishlist = st.pills(
        "Seleccioná tus faltantes",
        options=opciones_wishlist,
        default=current_wishlist_clean,
        selection_mode="multi",
        key=f"pills_wish_{country_name}",
        on_change=marcar_cambio
    )
    
    # Actualizamos estado
    state['wishlist'] = seleccion_wishlist

    st.markdown("---")
    
    # --- SECCIÓN 3: REPETIDAS (Tabla Dinámica) ---
    st.markdown("### 🔁 Mis Repetidas")
    st.caption("Definí precio o canje para tus repetidas (Solo de las que marcaste como 'Tengo').")
    
    # Solo permitimos cargar repetidas de las figuritas que el usuario dijo tener (Owned)
    posibles_repes = sorted(state['owned'])
    
    if not posibles_repes:
        st.info("👆 Primero marcá figuritas en la sección '¿Cuáles Tenés?' para poder cargar repetidas.")
    else:
        # Filtramos la data actual de repetidas para que sea coherente con lo que tiene
        # Si desmarcó una figu de 'Tengo', la borramos de 'Repes'
        state['repes'] = [r for r in state['repes'] if r['Figurita'] in posibles_repes]
        
        df_repes = pd.DataFrame(state['repes'])
        
        column_config = {
            "Figurita": st.column_config.SelectboxColumn(
                "Número", 
                options=posibles_repes, 
                required=True,
                help="Solo podés repetir las que tenés."
            ),
            "Modo": st.column_config.SelectboxColumn(
                "Objetivo", 
                options=["Canje", "Venta"], 
                required=True, 
                default="Canje"
            ),
            "Precio": st.column_config.NumberColumn(
                "Precio ($)", 
                min_value=0, 
                step=100, 
                default=0,
                format="$%d"
            ),
            "Cantidad": st.column_config.NumberColumn(
                "Cant.", 
                min_value=1, 
                step=1, 
                default=1
            )
        }
        
        # Editor de datos
        edited_df = st.data_editor(
            df_repes, 
            num_rows="dynamic", 
            column_config=column_config, 
            use_container_width=True, 
            key=f"editor_{country_name}",
            on_change=marcar_cambio # Detectar cambios en la tabla
        )
        
        # Guardamos cambios de la tabla en memoria
        if not edited_df.equals(pd.DataFrame(state['repes'])):
            state['repes'] = edited_df.to_dict('records')