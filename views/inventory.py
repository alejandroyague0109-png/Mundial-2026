import streamlit as st
import pandas as pd
import database as db
import utils

# Función auxiliar para marcar que hubo cambios
def marcar_cambio():
    st.session_state.unsaved_changes = True

def render_inventory(user, start, end, country_name):
    # Inicializamos la bandera de cambios si no existe
    if 'unsaved_changes' not in st.session_state:
        st.session_state.unsaved_changes = False

    # Obtenemos datos de la DB
    # IMPORTANTE: Usamos @st.cache_data en database para no saturar, 
    # pero aquí necesitamos datos frescos si acabamos de cambiar de país.
    db_tengo, db_wishlist, db_repes_info, df_full = db.get_inventory_status(user['id'], start, end)

    # Inicializamos estados de sesión para la UI si es la primera carga de este país
    # Usamos una clave única combinando el país para resetear la memoria visual
    session_key = f"inv_state_{country_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'owned': db_tengo,
            'wishlist': db_wishlist,
            'repes': [] 
        }
        # Pre-cargar repetidas en el formato del editor
        repes_rows = []
        for num, info in db_repes_info.items():
            modo = "Venta" if info['price'] > 0 else "Canje"
            repes_rows.append({
                "Figurita": num,
                "Modo": modo,
                "Precio": info['price'],
                "Cantidad": info['quantity']
            })
        st.session_state[session_key]['repes'] = repes_rows
        # Al cargar desde DB, no hay cambios sin guardar
        st.session_state.unsaved_changes = False

    # Alias para escribir menos
    state = st.session_state[session_key]

    # --- ENCABEZADO ---
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"{country_name} ({start}-{end})")
    
    # Botón Guardar con indicación visual
    btn_label = "💾 Guardar Cambios"
    if st.session_state.unsaved_changes:
        btn_label = "💾 Guardar Cambios (*)"
        
    if c2.button(btn_label, type="primary" if st.session_state.unsaved_changes else "secondary", use_container_width=True):
        with utils.spinner_futbolero():
            # Convertimos el editor de repetidas a DataFrame para guardar
            df_repes_tosave = pd.DataFrame(state['repes'])
            db.save_inventory_positive(user['id'], start, end, state['owned'], state['wishlist'], df_repes_tosave)
            st.session_state.unsaved_changes = False # Reset flag
        st.toast("¡Cambios guardados!", icon="✅")
        st.rerun()

    # --- GRILLA DE FIGURITAS ---
    numeros = range(start, end + 1)
    cols = st.columns(5) # 5 columnas para desktop
    
    for i, num in enumerate(numeros):
        with cols[i % 5]:
            # Determinamos estado actual
            status_val = None
            if num in state['owned']: status_val = "Tengo"
            elif num in state['wishlist']: status_val = "Falta"
            
            # Key única para el widget
            pill_key = f"p_{country_name}_{num}"
            
            # Renderizamos Pill
            # on_change=marcar_cambio activa la bandera roja
            selection = st.pills(
                str(num), 
                options=["Tengo", "Falta"], 
                default=status_val, 
                key=pill_key, 
                selection_mode="single", 
                label_visibility="collapsed",
                on_change=marcar_cambio 
            )
            
            # Actualizamos memoria local (Session State)
            if selection == "Tengo":
                if num not in state['owned']: state['owned'].append(num)
                if num in state['wishlist']: state['wishlist'].remove(num)
            elif selection == "Falta":
                if num in state['owned']: state['owned'].remove(num)
                if num not in state['wishlist']: state['wishlist'].append(num)
                # Si pasa a falta, borrar de repetidas si estaba
                state['repes'] = [r for r in state['repes'] if r['Figurita'] != num]
            else: # Selección vacía (click de nuevo para deseleccionar)
                if num in state['owned']: state['owned'].remove(num)
                if num in state['wishlist']: state['wishlist'].remove(num)

    st.divider()
    
    # --- SECCIÓN REPETIDAS ---
    st.subheader("🔁 Mis Repetidas")
    st.caption("Marcá arriba 'Tengo' para que aparezcan opciones.")
    
    # Filtramos solo las que el usuario dice que TIENE
    posibles_repes = sorted(state['owned'])
    
    if not posibles_repes:
        st.info("Primero marcá figuritas como 'Tengo' arriba.")
    else:
        # Preparamos data para el DataEditor
        # Sincronizamos: Si una figu ya no está en 'owned', la sacamos de repes
        state['repes'] = [r for r in state['repes'] if r['Figurita'] in posibles_repes]
        
        # Si hay nuevas 'owned' que no están en 'repes', no las agregamos automáticamente,
        # el usuario debe agregarlas manualmente si quiere venderlas.
        
        df_repes = pd.DataFrame(state['repes'])
        
        # Configuración de columnas
        column_config = {
            "Figurita": st.column_config.SelectboxColumn("Número", options=posibles_repes, required=True),
            "Modo": st.column_config.SelectboxColumn("Objetivo", options=["Canje", "Venta"], required=True, default="Canje"),
            "Precio": st.column_config.NumberColumn("Precio ($)", min_value=0, step=100, default=0),
            "Cantidad": st.column_config.NumberColumn("Cant.", min_value=1, step=1, default=1)
        }
        
        edited_df = st.data_editor(
            df_repes, 
            num_rows="dynamic", 
            column_config=column_config, 
            use_container_width=True, 
            key=f"editor_{country_name}",
            on_change=marcar_cambio # También detecta cambios aquí
        )
        
        # Guardamos el estado del editor en memoria
        if not edited_df.equals(pd.DataFrame(state['repes'])):
            state['repes'] = edited_df.to_dict('records')