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
    db_tengo, db_wishlist, db_repes_info, df_full = db.get_inventory_status(user['id'], start, end)

    # Inicializamos estados de sesión
    session_key = f"inv_state_{country_name}"
    
    if session_key not in st.session_state:
        st.session_state[session_key] = {
            'owned': db_tengo,
            'wishlist': db_wishlist,
            'repes': [] 
        }
        # Pre-cargar repetidas
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
        st.session_state.unsaved_changes = False

    # Alias
    state = st.session_state[session_key]

    # --- ENCABEZADO ---
    c1, c2 = st.columns([3, 1])
    c1.subheader(f"{country_name} ({start}-{end})")
    
    # Botón Guardar
    btn_label = "💾 Guardar Cambios"
    if st.session_state.unsaved_changes:
        btn_label = "💾 Guardar Cambios (*)"
        
    if c2.button(btn_label, type="primary" if st.session_state.unsaved_changes else "secondary", use_container_width=True):
        with utils.spinner_futbolero():
            df_repes_tosave = pd.DataFrame(state['repes'])
            db.save_inventory_positive(user['id'], start, end, state['owned'], state['wishlist'], df_repes_tosave)
            st.session_state.unsaved_changes = False
        st.toast("¡Cambios guardados!", icon="✅")
        st.rerun()

    # --- REFERENCIA VISUAL ---
    st.caption("Referencia: ✅ = La Tengo | 🎯 = Me Falta (Wishlist)")

    # --- GRILLA DE FIGURITAS ---
    numeros = range(start, end + 1)
    
    # Usamos 5 columnas para que quede prolijo
    cols = st.columns(5)
    
    for i, num in enumerate(numeros):
        with cols[i % 5]:
            # Determinamos estado actual
            status_val = None
            if num in state['owned']: status_val = "✅"
            elif num in state['wishlist']: status_val = "🎯"
            
            # Key única
            pill_key = f"p_{country_name}_{num}"
            
            # 1. MOSTRAR EL NÚMERO GRANDE
            st.markdown(f"<h4 style='text-align: center; margin: 0; padding: 0;'>{num}</h4>", unsafe_allow_html=True)
            
            # 2. SELECTOR CON ÍCONOS (Sin texto que ensucie)
            selection = st.pills(
                "Estado", # Label oculto
                options=["✅", "🎯"], 
                default=status_val, 
                key=pill_key, 
                selection_mode="single", 
                label_visibility="collapsed",
                on_change=marcar_cambio 
            )
            
            # Actualizamos memoria local
            if selection == "✅":
                if num not in state['owned']: state['owned'].append(num)
                if num in state['wishlist']: state['wishlist'].remove(num)
            elif selection == "🎯":
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
    st.caption("Marcá arriba con ✅ las que tenés para que aparezcan opciones.")
    
    posibles_repes = sorted(state['owned'])
    
    if not posibles_repes:
        st.info("Primero marcá figuritas como 'Tengo' (✅) arriba.")
    else:
        # Sincronizamos
        state['repes'] = [r for r in state['repes'] if r['Figurita'] in posibles_repes]
        
        df_repes = pd.DataFrame(state['repes'])
        
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
            on_change=marcar_cambio
        )
        
        if not edited_df.equals(pd.DataFrame(state['repes'])):
            state['repes'] = edited_df.to_dict('records')