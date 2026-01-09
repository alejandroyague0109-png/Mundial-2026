import streamlit as st
import pandas as pd
import database as db
import config
import utils
import time

# --- MODAL INFORMATIVO ---
@st.dialog("🎯 El Poder de la Wishlist")
def modal_info_wishlist():
    st.markdown("""
    ### ¿Por qué es clave marcar tus faltantes? 🤔
    
    **1. Para Usuarios FREE (Match Directo):**
    El sistema es como un radar. Solo te va a avisar que encontraste un cambio si sabe qué buscás.
    * Si vos tenés la **#10** y buscás la **#20**.
    * Y otro tiene la **#20** y busca la **#10**.
    * **¡BOOM! 💥 Match.** (Si no la marcás acá, el radar no suena).

    **2. Para Usuarios PREMIUM (Triangulación):**
    Acá ocurre la magia. Si nadie quiere tus repetidas directamente, la Wishlist permite hacer **carambolas a 3 bandas**:
    * Vos le das al **Puente**.
    * El **Puente** le da a tu **Objetivo**.
    * El **Objetivo** te da a **Vos**.
    
    > 💡 **Tip Pro:** ¡Mantené tu Wishlist actualizada para no perder oportunidades!
    """)

def save_changes(user_id, country_code, start, end, tengo_selection, wish_selection, df_repes):
    """Guarda los cambios en la base de datos."""
    with utils.spinner_futbolero():
        success, msg = db.save_inventory_positive(
            user_id, start, end, 
            tengo_selection, wish_selection, df_repes
        )
    if success:
        st.toast("¡Álbum actualizado!", icon="💾")
        # Actualizamos el snapshot
        st.session_state[f"snapshot_tengo_{country_code}"] = set(tengo_selection)
        st.session_state[f"snapshot_wish_{country_code}"] = set(wish_selection)
        # Limpiamos flags
        st.session_state.unsaved_changes = False
        time.sleep(0.5)
        st.rerun()
    else:
        st.error(f"Error al guardar: {msg}")

# CORRECCIÓN AQUÍ: Aceptamos los 4 argumentos que envía app_figuritas.py
def render_inventory(user, start_arg, end_arg, country_code_arg):
    
    # Sincronizamos el estado inicial si no existe
    if "current_country" not in st.session_state:
        st.session_state.current_country = country_code_arg

    st.subheader(f"📖 Mi Álbum: {st.session_state.current_country}")

    # 1. Selector de País/Álbum (Permite cambiar dinámicamente)
    countries = list(config.ALBUM_PAGES.keys())
    current_idx = countries.index(st.session_state.current_country) if st.session_state.current_country in countries else 0
    
    selected_country = st.selectbox(
        "Seleccioná el equipo/país:", 
        countries, 
        index=current_idx,
        key="sb_country_select"
    )

    # Detectar cambio de país y gestionar guardado
    if selected_country != st.session_state.current_country:
        if st.session_state.get("unsaved_changes", False):
            from views import modals
            modals.confirmar_cambio_pais(selected_country, user)
            return 
        else:
            st.session_state.current_country = selected_country
            st.rerun()

    # Recalculamos rangos basados en la selección actual (ignora los args antiguos si cambiaste de país)
    start, end = config.ALBUM_PAGES[st.session_state.current_country]
    all_stickers = [str(i) for i in range(start, end + 1)]

    # 2. Cargar Datos
    cache_key_tengo = f"pills_tengo_{selected_country}"
    cache_key_wish = f"pills_wish_{selected_country}"
    
    if cache_key_tengo not in st.session_state:
        with utils.spinner_futbolero():
            inventory_data = db.fetch_inventory(user['id'], start, end)
            
        tengo_db = set()
        wish_db = set()
        repes_rows = []

        for item in inventory_data:
            num = str(item['num'])
            status = item['status']
            
            if status == 'tengo':
                tengo_db.add(num)
            elif status == 'wishlist':
                wish_db.add(num)
            elif status in ['repetida', 'repe']:
                tengo_db.add(num) 
                repes_rows.append({
                    "Figurita": num,
                    "Estado": "Repetida",
                    "Precio": float(item.get('price', 0) or 0),
                    "Notas": ""
                })
        
        st.session_state[cache_key_tengo] = list(tengo_db)
        st.session_state[cache_key_wish] = list(wish_db)
        st.session_state[f"repes_df_{selected_country}"] = pd.DataFrame(repes_rows)
        
        st.session_state[f"snapshot_tengo_{selected_country}"] = tengo_db.copy()
        st.session_state[f"snapshot_wish_{selected_country}"] = wish_db.copy()

    # --- UI DE CARGA ---
    
    # A. SECCIÓN TENGO
    st.markdown("##### ✅ Mis Figuritas (Las que ya pegué)")
    st.caption("Marcá todas las que tenés en tu álbum.")
    
    selection_tengo = st.pills(
        "Tengo",
        options=all_stickers,
        selection_mode="multi",
        default=st.session_state[cache_key_tengo],
        key=cache_key_tengo,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # B. SECCIÓN WISHLIST (Con el botón de Info solicitado)
    col_w_txt, col_w_btn = st.columns([0.85, 0.15])
    
    with col_w_txt:
        st.markdown("##### ❤️ Wishlist (Tus Faltantes)")
        st.caption("Marcá las que **TE FALTAN** y querés conseguir urgente.")
    
    with col_w_btn:
        if st.button("ℹ️", key="btn_info_wishlist", help="¿Para qué sirve esto?"):
            modal_info_wishlist()

    selection_wish = st.pills(
        "Faltan",
        options=all_stickers,
        selection_mode="multi",
        default=st.session_state[cache_key_wish],
        key=cache_key_wish,
        label_visibility="collapsed"
    )
    
    overlap = set(selection_tengo) & set(selection_wish)
    if overlap:
        st.warning(f"⚠️ Cuidado: Marcaste estas figuritas como 'Tengo' y 'Deseo' al mismo tiempo: {', '.join(overlap)}")

    st.markdown("---")

    # C. SECCIÓN REPETIDAS
    st.markdown("##### 🔁 Mis Repetidas (Para Canje/Venta)")
    st.caption("Agregá acá las que te sobraron. Son las que verán los demás usuarios.")
    
    if f"repes_df_{selected_country}" not in st.session_state:
        st.session_state[f"repes_df_{selected_country}"] = pd.DataFrame(columns=["Figurita", "Estado", "Precio", "Notas"])

    df_editor = st.data_editor(
        st.session_state[f"repes_df_{selected_country}"],
        num_rows="dynamic",
        column_config={
            "Figurita": st.column_config.TextColumn("Número #", required=True, validate=r"^\d+$"),
            "Estado": st.column_config.SelectboxColumn("Disponibilidad", options=["Repetida"], required=True, default="Repetida"),
            "Precio": st.column_config.NumberColumn("Precio ($)", min_value=0, step=100, format="$%d"),
            "Notas": st.column_config.TextColumn("Notas (Opcional)")
        },
        use_container_width=True,
        key=f"editor_{selected_country}"
    )

    # --- BOTÓN DE GUARDADO ---
    st.markdown("###")
    
    has_changes = False
    if set(selection_tengo) != st.session_state[f"snapshot_tengo_{selected_country}"]: has_changes = True
    if set(selection_wish) != st.session_state[f"snapshot_wish_{selected_country}"]: has_changes = True
    
    col_save, _ = st.columns([0.5, 0.5])
    if col_save.button("💾 Guardar Cambios", type="primary", use_container_width=True):
        save_changes(
            user['id'], 
            selected_country, 
            start, end, 
            selection_tengo, 
            selection_wish, 
            df_editor
        )
        
    if has_changes:
        st.session_state.unsaved_changes = True