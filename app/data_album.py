# app/data_album.py

# Estructura del Álbum (Figus 26)
# "CODIGO": {"name": "Nombre Visible", "start": ID_Global, "count": Cantidad}
# La lógica es secuencial: El start del siguiente es (start anterior + count anterior)

ALBUM_STRUCTURE = {
    # --- INTRODUCCIÓN ---
    "FWC": {"name": "Intro", "start": 1, "count": 18},
    
    # --- CABEZAS DE SERIE & ANFITRIONES 2026 ---
    
    "MEX": {"name": "México 🇲🇽", "start": 19, "count": 20},
    "SUD": {"name": "Sudafrica 🇿🇦", "start": 39, "count": 20},
    "KOR": {"name": "Corea del Sur 🇰🇷", "start": 59, "count": 20},
    "RE1": {"name": "Repechaje 1 🏴", "start": 79, "count": 20},

    "CAN": {"name": "Canadá 🇨🇦", "start": 99, "count": 20},    
    "RE2": {"name": "Repechaje 2 🏴", "start": 119, "count": 20},
    "QAT": {"name": "Catar 🇶🇦", "start": 139, "count": 20},
    "SUI": {"name": "Suiza 🇨🇭", "start": 159, "count": 20},

    "BRA": {"name": "Brasil 🇧🇷", "start": 179, "count": 20},
    "MAR": {"name": "Marruecos 🇲🇦", "start": 199, "count": 20},
    "HAI": {"name": "Haití 🇭🇹", "start": 219, "count": 20},
    "ESC": {"name": "Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿", "start": 239, "count": 20}, 
   
    "USA": {"name": "USA 🇺🇸", "start": 259, "count": 20},
    "PAR": {"name": "Paraguay 🇵🇾", "start": 279, "count": 20},
    "AUS": {"name": "Australia 🇦🇺", "start": 299, "count": 20},
    "RE3": {"name": "Repechaje 3 🏴", "start": 319, "count": 20},   

    "GER": {"name": "Alemania 🇩🇪", "start": 339, "count": 20},
    "CUR": {"name": "Curazao 🇨🇼", "start": 359, "count": 20},
    "COT": {"name": "Costa de Marfil 🇨🇮", "start": 379, "count": 20},
    "ECU": {"name": "Ecuador 🇪🇨", "start": 399, "count": 20},

    "NED": {"name": "Países Bajos 🇳🇱", "start": 419, "count": 20},
    "JPN": {"name": "Japón 🇯🇵", "start": 439, "count": 20},
    "RE4": {"name": "Repechaje 4 🏴", "start": 459, "count": 20},
    "TUN": {"name": "Túnez 🇹🇳", "start": 479, "count": 20},

    "BEL": {"name": "Bélgica 🇧🇪", "start": 499, "count": 20},
    "EGI": {"name": "Egipto 🇪🇬", "start": 519, "count": 20},
    "IRN": {"name": "Irán 🇮🇷", "start": 539, "count": 20},
    "NZE": {"name": "Nueva Zelanda 🇳🇿", "start": 559, "count": 20},

    "ESP": {"name": "España 🇪🇸", "start": 579, "count": 20},
    "CAB": {"name": "Cabo Verde 🇨🇻", "start": 599, "count": 20},
    "KSA": {"name": "Arabia Saudita 🇸🇦", "start": 619, "count": 20},
    "URU": {"name": "Uruguay 🇺🇾", "start": 639, "count": 20},    

    "FRA": {"name": "Francia 🇫🇷", "start": 659, "count": 20},
    "SEN": {"name": "Senegal 🇸🇳", "start": 679, "count": 20},
    "RE5": {"name": "Repechaje 5 🏴", "start": 699, "count": 20},        
    "NOR": {"name": "Noruega 🇳🇴", "start": 719, "count": 20},

    "ARG": {"name": "Argentina 🇦🇷", "start": 739, "count": 20},
    "ALG": {"name": "Argelia 🇩🇿", "start": 759, "count": 20},
    "AUT": {"name": "Austria 🇦🇹", "start": 779, "count": 20},
    "JOR": {"name": "Jordania 🇯🇴", "start": 799, "count": 20},
    
    "POR": {"name": "Portugal 🇵🇹", "start": 819, "count": 20},
    "RE6": {"name": "Repechaje 6 🏴", "start": 839, "count": 20},        
    "UZB": {"name": "Uzbekistán 🇺🇿", "start": 859, "count": 20},
    "COL": {"name": "Colombia 🇨🇴", "start": 879, "count": 20},    

    "ENG": {"name": "Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿", "start": 899, "count": 20},
    "CRO": {"name": "Croacia 🇭🇷", "start": 919, "count": 20},
    "GHA": {"name": "Ghana 🇬🇭", "start": 939, "count": 20},
    "PAN": {"name": "Panamá 🇵🇦", "start": 959, "count": 20},
    
    # --- ESPECIALES COCA-COLA ---
    "COCA": {"name": "Coca-Cola Specials 🥤", "start": 979, "count": 2},
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