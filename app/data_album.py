# app/data_album.py

# Estructura del Álbum (Figus 26)
# "CODIGO": {"name": "Nombre Visible", "start": ID_Global, "count": Cantidad}
# La lógica es secuencial: El start del siguiente es (start anterior + count anterior)

ALBUM_STRUCTURE = {
    # --- INTRODUCCIÓN ---
    "FWC": {"name": "Intro / Museos", "start": 1, "count": 18},
    
    # --- CABEZAS DE SERIE & ANFITRIONES 2026 ---
    "ARG": {"name": "Argentina 🇦🇷", "start": 19, "count": 20},
    "BRA": {"name": "Brasil 🇧🇷", "start": 39, "count": 20},
    "USA": {"name": "USA 🇺🇸", "start": 59, "count": 20},
    "MEX": {"name": "México 🇲🇽", "start": 79, "count": 20},
    "CAN": {"name": "Canadá 🇨🇦", "start": 99, "count": 20},
    
    # --- EUROPA (UEFA) ---
    "FRA": {"name": "Francia 🇫🇷", "start": 119, "count": 20},
    "ENG": {"name": "Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿", "start": 139, "count": 20},
    "ESP": {"name": "España 🇪🇸", "start": 159, "count": 20},
    "GER": {"name": "Alemania 🇩🇪", "start": 179, "count": 20},
    "NED": {"name": "Países Bajos 🇳🇱", "start": 199, "count": 20},
    "POR": {"name": "Portugal 🇵🇹", "start": 219, "count": 20},
    "CRO": {"name": "Croacia 🇭🇷", "start": 239, "count": 20},
    "BEL": {"name": "Bélgica 🇧🇪", "start": 259, "count": 20},
    
    # --- SUDAMÉRICA (CONMEBOL) ---
    "URU": {"name": "Uruguay 🇺🇾", "start": 279, "count": 20},
    "ECU": {"name": "Ecuador 🇪🇨", "start": 299, "count": 20},
    
    # --- OTROS ---
    "MAR": {"name": "Marruecos 🇲🇦", "start": 319, "count": 20},
    "JPN": {"name": "Japón 🇯🇵", "start": 339, "count": 20},
    "KOR": {"name": "Corea del Sur 🇰🇷", "start": 359, "count": 20},
    "SEN": {"name": "Senegal 🇸🇳", "start": 379, "count": 20},
    "AUS": {"name": "Australia 🇦🇺", "start": 399, "count": 20},
    
    # --- ESPECIALES COCA-COLA ---
    "COCA": {"name": "Coca-Cola Specials", "start": 419, "count": 8},
}

# --- LÓGICA DE COMPATIBILIDAD ---
# Agregamos automáticamente el 'range' para que el frontend sepa dónde iterar
for code, data in ALBUM_STRUCTURE.items():
    # range(start, end) en Python excluye el final, por eso sumamos el count
    # Ejemplo: Start 1, Count 18 -> range(1, 19) -> Sticker 1 al 18
    data["range"] = (data["start"], data["start"] + data["count"] - 1)

def get_country_by_sticker(global_number: int):
    """
    Dado un número global de figurita (ej: 25), devuelve el nombre del país (ej: Argentina).
    """
    for code, data in ALBUM_STRUCTURE.items():
        if data["start"] <= global_number < data["start"] + data["count"]:
            return data["name"]
    return "Desconocido"