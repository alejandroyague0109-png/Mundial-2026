import streamlit as st
import pandas as pd
import time
import database as db
import utils 

# --- MODAL DE INFORMACIÓN (NUEVO) ---
@st.dialog("🎯 El Poder de la Wishlist")
def modal_info_wishlist():
    st.markdown("""
    ### ¿Por qué es clave marcar tus faltantes? 🤔
    
    **1. Para TODOS (Prioridad y Compartir):**
    ¡Organizá tu búsqueda! 📋
    * **🚀 Prioridad:** En el Mercado, las figuritas que marcás acá aparecen **PRIMERAS**.
    * **📲 WhatsApp:** Te sirve para tener tu lista de faltantes siempre a mano y compartirla rápido por WhatsApp con tus amigos.

    **2. Para PREMIUM (Alertas y Triangulación):**
    Desbloqueá la inteligencia artificial del álbum 🤖.
    * **🔔 Alertas:** El sistema te **notifica automáticamente** cuando alguien publica una figurita de tu Wishlist.
    * **📐 Triangulación:** Habilita el canje a 3 bandas (Vos -> Puente -> Objetivo) cuando no hay cambio directo.
    """)

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
    
    # INYECCIÓN CSS: BOTÓN "NINGUNA" (ROJO)
    # Apuntamos al botón en la tercera columna del bloque horizontal (col_btn_none)
    st.markdown("""
        <style>
        /* Estado Normal: Borde Rojo, Texto Rojo */
        div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-of-type(3) button {
            border-color: #FF4B4B !important;
            color: #FF4B4B !important;
        }
        /* Estado Hover: Fondo Rojo, Texto Blanco */
        div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-of-type(3) button:hover {
            border-color: #FF4B4B !important;
            background-color: #FF4B4B !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col_head_1, col_btn_all, col_btn_none = st.columns([4, 1, 1])
    col_head_1.markdown("### 1️⃣ Tus Figus")

    # Botón "Todas" -> VERDE (Primary)
    if col_btn_all.button("Todas", type="primary", use_container_width=True, key=f"all_{seleccion_pais}"):
        st.session_state[key_pills] = list(range(start, end + 1))
        st.session_state[key_wish] = [] 
        st.session_state.unsaved_changes = True 
        st.rerun()

    # Botón "Ninguna" -> ROJO (Estilo inyectado arriba)
    if col_btn_none.button("Ninguna", use_container_width=True, key=f"none_{seleccion_pais}"):
        st.session_state[key_pills] = []
        st.session_state.unsaved_changes = True 
        st.rerun()

    # --- WIDGET TENGO ---
    seleccion_tengo = st.pills(
        "Tengo", 
        list(range(start, end + 1)), 
        selection_mode="multi", 
        key=key_pills, 
        label_visibility="collapsed",
        on_change=marcar_cambio 
    )

    # --- SECCIÓN WISHLIST (CON BOTÓN INFO INTEGRADO) ---
    st.divider()
    
    # Layout para texto + botón info
    col_w_txt, col_w_btn = st.columns([0.85, 0.15])
    
    with col_w_txt:
        st.markdown("### ❤️ Wishlist (Prioridad)")
        st.caption("Marcá las que **TE FALTAN** y querés conseguir urgente.")
    
    with col_w_btn:
        # Botón que abre el modal explicativo
        if st.button("ℹ️", key="btn_info_wishlist", help="¿Para qué sirve la Wishlist?"):
            modal_info_wishlist()
    
    todas = set(range(start, end + 1))
    tengo_set = set(seleccion_tengo) if seleccion_tengo else set()
    faltantes = sorted(list(todas - tengo_set))
    
    current_wish = st.session_state.get(key_wish, [])
    clean_wish = [x for x in current_wish if x in faltantes]
    st.session_state[key_wish] = clean_wish
    
    # Widget Wishlist
    seleccion_wishlist = st.pills(
        "Deseo", 
        faltantes, 
        selection_mode="multi", 
        key=key_wish,
        on_change=marcar_cambio 
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

    # Widget Repes
    seleccion_repes = st.pills(
        "Repes", 
        posibles_repes, 
        selection_mode="multi", 
        key=key_repes,
        on_change=marcar_cambio 
    )

    # --- EDITOR DE DATOS ---
    edited_df = pd.DataFrame()
    if seleccion_repes:
        st.info("👇 **Data:** Hacé doble clic en 'Modo' para cambiar entre **Canje** y **Venta**.")
        data = []
        
        # Ordenamos la tabla
        for n in sorted(seleccion_repes):
            info = repetidas_info.get(n, {})
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
            key=f"editor_{seleccion_pais}",
            on_change=marcar_cambio 
        )
    
    # --- SNAPSHOT PARA DETECTAR CAMBIOS ---
    st.session_state[f"snapshot_df_{seleccion_pais}"] = edited_df

    st.divider()

    # --- BOTÓN GUARDAR (Dinámico: Verde si hay cambios) ---
    btn_type = "primary" if st.session_state.get('unsaved_changes', False) else "secondary"
    btn_lbl = "💾 GUARDAR CAMBIOS (*)" if st.session_state.get('unsaved_changes', False) else "💾 GUARDAR CAMBIOS"

    if st.button(btn_lbl, type=btn_type, use_container_width=True):
        with utils.spinner_futbolero():
            db.save_inventory_positive(user['id'], start, end, seleccion_tengo, seleccion_wishlist, edited_df)
            st.session_state.unsaved_changes = False 
        
        st.toast("¡Cambios guardados!", icon="✅")
        time.sleep(0.5)
        st.rerun()