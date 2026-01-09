import pandas as pd
import database as db

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    Busca triangulación con validación de zona flexible (strip).
    """
    # Normalizamos mi ubicación (quitar espacios extra)
    mi_provincia = str(user.get('province', '')).strip()
    mi_zona = str(user.get('zone', '')).strip()

    # 1. ENCONTRAR TARGETS
    raw_targets = db.get_users_with_sticker(figu_objetivo)
    
    targets_validos = []
    target_ids = []
    
    for t in raw_targets:
        if t['user_id'] != user['id']:
            # Comparación flexible de zona
            t_prov = str(t['province']).strip()
            t_zona = str(t['zone']).strip()
            
            if t_prov == mi_provincia and t_zona == mi_zona:
                targets_validos.append(t)
                target_ids.append(t['user_id'])
    
    if not target_ids:
        return [] 

    # 2. OBTENER WISHLIST
    targets_wishlists = db.get_wishlists_of_users(target_ids)
    
    # 3. BUSCAR EL PUENTE
    figus_necesarias = set()
    for t_id, deseos in targets_wishlists.items():
        figus_necesarias.update(deseos)
        
    if not figus_necesarias:
        return []

    posibles_puentes = db.find_potential_bridges(list(figus_necesarias), mis_repes_ids)
    
    posibles_triangulaciones = []

    # 4. ARMAR EL ROMPECABEZAS
    for puente in posibles_puentes:
        # Comparación flexible de zona para el puente también
        p_prov = str(puente['province']).strip()
        p_zona = str(puente['zone']).strip()

        if p_prov != mi_provincia or p_zona != mi_zona:
            continue

        bridge_uid = puente['user_id']
        bridge_tiene = puente['has_figu'] 
        bridge_quiere = puente['wants_figu'] 
        
        for t_id, deseos in targets_wishlists.items():
            if bridge_tiene in deseos:
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