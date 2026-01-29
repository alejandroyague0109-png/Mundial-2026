import database as db

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    [OPTIMIZADO]
    Esta función ya no calcula nada pesado. 
    Solo llama al motor SQL (PostgreSQL) que ya hizo el trabajo de grafos.
    """
    if not user or 'id' not in user:
        return []

    # 1. Llamada Única a Base de Datos (Eficiencia Máxima)
    # Esto ejecuta la función recursiva en el servidor
    raw_triangulations = db.get_triangulations_sql(user['id'])
    
    triangulaciones = []

    # 2. Procesamiento ligero de respuesta
    for row in raw_triangulations:
        # La función SQL devuelve cadenas genéricas encontradas.
        # Aquí filtramos: ¿Esta cadena termina dándome la figurita que quiero?
        
        # Nota: Ajustamos los nombres de las columnas según lo que devuelva tu SQL final.
        # Asumimos que el SQL devuelve: 
        # step1 (Puente), step2 (Target), sticker_to_me (Lo que recibo)
        
        sticker_que_recibo = int(row.get('step3_sticker', 0)) # La que tiene el Target
        
        # Si buscamos una específica y esta cadena no la tiene, la saltamos.
        if figu_objetivo and sticker_que_recibo != int(figu_objetivo):
            continue

        # 3. Formateo para la UI
        cadena = {
            "tipo": "triangulacion",
            
            # DATOS DEL TARGET (El que tiene la que quiero) [C]
            "target_id": row.get('step2_user_id'), 
            "target_nick": row.get('step2_user', 'Usuario'), # Ajustado al SQL básico
            "target_phone_enc": row.get('step2_phone', ''),
            "target_tiene": sticker_que_recibo,
            
            # DATOS DEL PUENTE (El intermediario) [B]
            "bridge_id": row.get('step1_user_id'),
            "bridge_nick": row.get('step1_user', 'Puente'),
            "bridge_phone_enc": row.get('step1_phone', ''),
            "bridge_tiene": int(row.get('step2_sticker', 0)), # Lo que le da al Target
            "bridge_quiere": int(row.get('step1_sticker', 0)) # Lo que yo le doy al Puente
        }
        triangulaciones.append(cadena)

    return triangulaciones