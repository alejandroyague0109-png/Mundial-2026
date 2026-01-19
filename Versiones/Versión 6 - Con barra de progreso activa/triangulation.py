import database as db

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    Busca cadenas: YO -> PUENTE -> TARGET -> YO
    """
    # 1. Filtros de ubicación
    mi_provincia = str(user.get('province', '')).strip()
    mi_zona = str(user.get('zone', '')).strip()

    # 2. Buscar TARGETS (Usuarios que tienen la que yo quiero)
    # db.get_users_with_sticker devuelve users con 'phone_encrypted'
    raw_targets = db.get_users_with_sticker(figu_objetivo)
    
    targets_validos = []
    target_ids = []
    
    for t in raw_targets:
        if t['user_id'] != user['id']:
            # Filtrar por zona para facilitar logística
            t_prov = str(t['province']).strip()
            t_zona = str(t['zone']).strip()
            
            if t_prov == mi_provincia and t_zona == mi_zona:
                targets_validos.append(t)
                target_ids.append(t['user_id'])
    
    if not target_ids:
        return [] 

    # 3. Obtener Wishlists de los Targets (¿Qué quieren ellos?)
    targets_wishlists = db.get_wishlists_of_users(target_ids)
    
    # 4. Identificar qué figuritas buscan mis Targets
    figus_necesarias_por_targets = set()
    for t_id, deseos in targets_wishlists.items():
        figus_necesarias_por_targets.update(deseos)
        
    if not figus_necesarias_por_targets:
        return []

    # 5. Buscar PUENTES
    # Buscamos usuarios que TENGAN lo que quieren mis Targets y QUIERAN lo que YO tengo
    posibles_puentes = db.find_potential_bridges(list(figus_necesarias_por_targets), mis_repes_ids)
    
    triangulaciones = []

    # 6. Armar las cadenas
    for puente in posibles_puentes:
        p_prov = str(puente['province']).strip()
        p_zona = str(puente['zone']).strip()

        # El puente también debe ser de la zona
        if p_prov != mi_provincia or p_zona != mi_zona:
            continue

        bridge_uid = puente['user_id']
        bridge_tiene = puente['has_figu']   # Lo que el puente tiene (y el Target quiere)
        bridge_quiere = puente['wants_figu'] # Lo que el puente quiere (y Yo tengo)
        
        # Cruzar con los Targets
        for t_id, deseos in targets_wishlists.items():
            if bridge_tiene in deseos:
                # Encontramos match: Puente tiene lo que Target busca
                target_info = next((t for t in targets_validos if t['user_id'] == t_id), None)
                
                if target_info:
                    cadena = {
                        "tipo": "triangulacion",
                        
                        # Datos del Objetivo (Target)
                        "target_id": t_id,
                        "target_nick": target_info.get('nick', 'Vecino'),
                        "target_phone_enc": target_info.get('phone_encrypted', ''),
                        "target_tiene": figu_objetivo, # Lo que yo recibo
                        
                        # Datos del Puente (Bridge)
                        "bridge_id": bridge_uid,
                        "bridge_nick": puente['nick'],
                        "bridge_phone_enc": puente.get('phone_encrypted', ''),
                        "bridge_tiene": bridge_tiene,  # Lo que puente entrega a target
                        "bridge_quiere": bridge_quiere # Lo que yo entrego a puente
                    }
                    triangulaciones.append(cadena)
                    
                    # Limitamos a 5 resultados para no saturar
                    if len(triangulaciones) >= 5:
                        return triangulaciones

    return triangulaciones