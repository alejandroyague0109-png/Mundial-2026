import pandas as pd
import database as db

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    Busca triangulación CON RESTRICCIÓN GEOGRÁFICA.
    Todos (Yo, Puente, Target) deben estar en la misma Provincia y Zona.
    """
    mi_provincia = user.get('province')
    mi_zona = user.get('zone')

    # 1. ENCONTRAR TARGETS (Dueños de la figu que quiero)
    raw_targets = db.get_users_with_sticker(figu_objetivo)
    
    # FILTRO GEOGRÁFICO NIVEL 1: El Target debe ser de mi zona
    targets_validos = []
    target_ids = []
    
    for t in raw_targets:
        if t['user_id'] != user['id']:
            if t['province'] == mi_provincia and t['zone'] == mi_zona:
                targets_validos.append(t)
                target_ids.append(t['user_id'])
    
    if not target_ids:
        return [] # Nadie en tu zona tiene esa figurita

    # 2. OBTENER WISHLIST DE LOS TARGETS
    targets_wishlists = db.get_wishlists_of_users(target_ids)
    
    # 3. BUSCAR EL PUENTE (Candidatos globales que tienen lo que el target quiere)
    figus_necesarias = set()
    for t_id, deseos in targets_wishlists.items():
        figus_necesarias.update(deseos)
        
    if not figus_necesarias:
        return []

    posibles_puentes_raw = db.find_potential_bridges(list(figus_necesarias), mis_repes_ids)
    
    posibles_triangulaciones = []

    # 4. ARMAR EL ROMPECABEZAS CON FILTRO GEOGRÁFICO NIVEL 2
    for puente in posibles_puentes_raw:
        # FILTRO: El Puente TAMBIÉN debe ser de mi zona
        if puente['province'] != mi_provincia or puente['zone'] != mi_zona:
            continue

        bridge_uid = puente['user_id']
        bridge_tiene = puente['has_figu'] 
        bridge_quiere = puente['wants_figu'] 
        
        # Verificar si lo que tiene el puente le sirve a un Target de mi zona
        for t_id, deseos in targets_wishlists.items():
            if bridge_tiene in deseos:
                # Recuperar info del target (ya filtrado por zona en paso 1)
                target_info = next((t for t in targets_validos if t['user_id'] == t_id), None)
                
                if target_info:
                    cadena = {
                        "tipo": "triangulacion",
                        "target_id": t_id,
                        "target_nick": target_info.get('nick', 'Vecino'),
                        "target_tiene": figu_objetivo,
                        
                        "bridge_id": bridge_uid,
                        "bridge_nick": puente['nick'],
                        "bridge_tiene": bridge_tiene,
                        "bridge_quiere": bridge_quiere,
                    }
                    posibles_triangulaciones.append(cadena)
                    
                    if len(posibles_triangulaciones) >= 5:
                        return posibles_triangulaciones

    return posibles_triangulaciones