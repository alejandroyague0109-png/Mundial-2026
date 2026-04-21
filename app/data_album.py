# app/data_album.py

# Estructura del Álbum (Figus 26)
# "CODIGO": {"name": "Nombre Visible", "start": ID_Global, "count": Cantidad}
# La lógica es secuencial: El start del siguiente es (start anterior + count anterior)

ALBUM_STRUCTURE = {
    # --- INTRODUCCIÓN ---
    "FWC": {"name": "Intro", "start": 1, "count": 20},
    
    # --- CABEZAS DE SERIE & ANFITRIONES 2026 ---
    
    "MEX": {"name": "México 🇲🇽", "start": 21, "count": 20},
    "SUD": {"name": "Sudafrica 🇿🇦", "start": 41, "count": 20},
    "KOR": {"name": "Corea del Sur 🇰🇷", "start": 61, "count": 20},
    "RCZ": {"name": "Rep Checa 🇨🇿", "start": 81, "count": 20},

    "CAN": {"name": "Canadá 🇨🇦", "start": 101, "count": 20},    
    "BYH": {"name": "Bosnia 🇧🇦", "start": 121, "count": 20},
    "QAT": {"name": "Catar 🇶🇦", "start": 141, "count": 20},
    "SUI": {"name": "Suiza 🇨🇭", "start": 161, "count": 20},

    "BRA": {"name": "Brasil 🇧🇷", "start": 181, "count": 20},
    "MAR": {"name": "Marruecos 🇲🇦", "start": 201, "count": 20},
    "HAI": {"name": "Haití 🇭🇹", "start": 221, "count": 20},
    "ESC": {"name": "Escocia 🏴󠁧󠁢󠁳󠁣󠁴󠁿", "start": 241, "count": 20}, 
   
    "USA": {"name": "USA 🇺🇸", "start": 261, "count": 20},
    "PAR": {"name": "Paraguay 🇵🇾", "start": 281, "count": 20},
    "AUS": {"name": "Australia 🇦🇺", "start": 301, "count": 20},
    "TUR": {"name": "Turquía 🇹🇷", "start": 321, "count": 20},   

    "GER": {"name": "Alemania 🇩🇪", "start": 341, "count": 20},
    "CUR": {"name": "Curazao 🇨🇼", "start": 361, "count": 20},
    "COT": {"name": "Costa de Marfil 🇨🇮", "start": 381, "count": 20},
    "ECU": {"name": "Ecuador 🇪🇨", "start": 401, "count": 20},

    "NED": {"name": "Países Bajos 🇳🇱", "start": 421, "count": 20},
    "JPN": {"name": "Japón 🇯🇵", "start": 441, "count": 20},
    "SUE": {"name": "Suecia 🇸🇪", "start": 461, "count": 20},
    "TUN": {"name": "Túnez 🇹🇳", "start": 481, "count": 20},

    "BEL": {"name": "Bélgica 🇧🇪", "start": 501, "count": 20},
    "EGI": {"name": "Egipto 🇪🇬", "start": 521, "count": 20},
    "IRN": {"name": "Irán 🇮🇷", "start": 541, "count": 20},
    "NZE": {"name": "Nueva Zelanda 🇳🇿", "start": 561, "count": 20},

    "ESP": {"name": "España 🇪🇸", "start": 581, "count": 20},
    "CAB": {"name": "Cabo Verde 🇨🇻", "start": 601, "count": 20},
    "KSA": {"name": "Arabia Saudita 🇸🇦", "start": 621, "count": 20},
    "URU": {"name": "Uruguay 🇺🇾", "start": 641, "count": 20},    

    "FRA": {"name": "Francia 🇫🇷", "start": 661, "count": 20},
    "SEN": {"name": "Senegal 🇸🇳", "start": 681, "count": 20},
    "IRK": {"name": "Irak 🇮🇶", "start": 701, "count": 20},        
    "NOR": {"name": "Noruega 🇳🇴", "start": 721, "count": 20},

    "ARG": {"name": "Argentina 🇦🇷", "start": 741, "count": 20},
    "ALG": {"name": "Argelia 🇩🇿", "start": 761, "count": 20},
    "AUT": {"name": "Austria 🇦🇹", "start": 781, "count": 20},
    "JOR": {"name": "Jordania 🇯🇴", "start": 801, "count": 20},
    
    "POR": {"name": "Portugal 🇵🇹", "start": 821, "count": 20},
    "RDC": {"name": "Rep Dem Congo 🇨🇩", "start": 841, "count": 20},        
    "UZB": {"name": "Uzbekistán 🇺🇿", "start": 861, "count": 20},
    "COL": {"name": "Colombia 🇨🇴", "start": 881, "count": 20},    

    "ENG": {"name": "Inglaterra 🏴󠁧󠁢󠁥󠁮󠁧󠁿", "start": 901, "count": 20},
    "CRO": {"name": "Croacia 🇭🇷", "start": 921, "count": 20},
    "GHA": {"name": "Ghana 🇬🇭", "start": 941, "count": 20},
    "PAN": {"name": "Panamá 🇵🇦", "start": 961, "count": 20},
    
    # --- ESPECIALES COCA-COLA ---
    "COCA": {"name": "Coca-Cola Specials 🥤", "start": 981, "count": 14},
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