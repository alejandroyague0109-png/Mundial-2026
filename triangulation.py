import pandas as pd
import database as db
import streamlit as st # Importamos st para mostrar los mensajes de debug

def buscar_triangulacion(user, figu_objetivo, mis_repes_ids):
    """
    VERSIÓN DE DEBUGGING: Muestra el paso a paso en pantalla.
    """
    mi_provincia = user.get('province')
    mi_zona = user.get('zone')
    
    st.warning(f"🕵️‍♂️ DEBUG START:")
    st.write(f"1. Yo soy {user['nick']} ({user['id']}) en {mi_provincia} - {mi_zona}")
    st.write(f"2. Busco la #{figu_objetivo}")
    st.write(f"3. Ofrezco (mis repes): {mis_repes_ids}")

    # 1. ENCONTRAR TARGETS
    raw_targets = db.get_users_with_sticker(figu_objetivo)
    st.write(f"4. Usuarios con la #{figu_objetivo} (Total DB): {len(raw_targets)}")
    
    targets_validos = []
    target_ids = []
    
    for t in raw_targets:
        # Debuggeo de cada candidato
        es_mismo_user = (t['user_id'] == user['id'])
        misma_prov = (t['province'] == mi_provincia)
        misma_zona = (t['zone'] == mi_zona)
        
        if not es_mismo_user and misma_prov and misma_zona:
            targets_validos.append(t)
            target_ids.append(t['user_id'])
        else:
            # Mostrar por qué se descartó
            st.caption(f"❌ Descartado {t['nick']}: MismoUser={es_mismo_user}, Prov={t['province']}=={mi_provincia}, Zona={t['zone']}=={mi_zona}")
    
    st.write(f"5. Targets válidos en tu zona: {len(targets_validos)} IDs: {target_ids}")

    if not target_ids:
        st.error("🛑 Corte: No hay nadie en tu zona que tenga la figurita.")
        return []

    # 2. OBTENER WISHLIST DE TARGETS
    targets_wishlists = db.get_wishlists_of_users(target_ids)
    st.write(f"6. Wishlists de los Targets: {targets_wishlists}")
    
    # 3. BUSCAR EL PUENTE
    figus_necesarias = set()
    for t_id, deseos in targets_wishlists.items():
        figus_necesarias.update(deseos)
        
    st.write(f"7. Necesitamos un Puente que tenga alguna de estas: {figus_necesarias}")
    st.write(f"   ... Y que quiera alguna de estas (las mías): {mis_repes_ids}")

    if not figus_necesarias:
        st.error("🛑 Corte: Los Targets no tienen nada en su Wishlist.")
        return []

    posibles_puentes_raw = db.find_potential_bridges(list(figus_necesarias), mis_repes_ids)
    st.write(f"8. Puentes encontrados (Raw): {len(posibles_puentes_raw)}")

    posibles_triangulaciones = []

    # 4. ARMAR EL ROMPECABEZAS
    for puente in posibles_puentes_raw:
        st.write(f"   -> Analizando Puente: {puente['nick']} ({puente['province']} - {puente['zone']})")
        
        if puente['province'] != mi_provincia or puente['zone'] != mi_zona:
            st.caption(f"      ❌ Descartado por zona incorrecta.")
            continue

        bridge_uid = puente['user_id']
        bridge_tiene = puente['has_figu'] 
        bridge_quiere = puente['wants_figu'] 
        
        for t_id, deseos in targets_wishlists.items():
            if bridge_tiene in deseos:
                target_info = next((t for t in targets_validos if t['user_id'] == t_id), None)
                if target_info:
                    st.success(f"      ✅ ¡MATCH! {puente['nick']} tiene la {bridge_tiene} que quiere {target_info['nick']}")
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

    st.write(f"🏁 Resultado final: {len(posibles_triangulaciones)} triangulaciones.")
    return posibles_triangulaciones