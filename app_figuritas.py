# ... código anterior ...

# --- PÁGINA PRINCIPAL ---
st.header("📖 Mi Álbum")

print("--- DEBUG: INICIO DE PÁGINA PRINCIPAL ---") # <--- AGREGAR ESTO

# Selector de país
seleccion = st.selectbox("Selecciona Sección:", list(ALBUM_PAGES.keys()), key="seleccion_pais_key")

# BARRA LOCAL
start_active, end_active = ALBUM_PAGES[seleccion]
numeros_posibles = list(range(start_active, end_active + 1))

print(f"--- DEBUG: CONSULTANDO SUPABASE PARA {seleccion} ---") # <--- AGREGAR ESTO

# Obtenemos estado actual
# AQUÍ ES DONDE PROBABLEMENTE SE TRABA
ids_tengo, repetidas_info, df_full = get_inventory_status(user['id'], start_active, end_active)

print("--- DEBUG: SUPABASE RESPONDIÓ ---") # <--- AGREGAR ESTO

# Progreso Local
tengo_sec = len(ids_tengo)
# ... resto del código ...