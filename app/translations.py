# app/translations.py

# Diccionario maestro de términos locales
TRANSLATIONS = {
    "figuritas": {
        "AR": "figuritas",
        "UY": "figuritas",
        "MX": "estampas",
        "CL": "láminas",
        "CO": "láminas",
        "ES": "cromos",
        "default": "figuritas"
    },
    "figurita": {
        "AR": "figurita",
        "UY": "figurita",
        "MX": "estampa",
        "CL": "lámina",
        "CO": "lámina",
        "ES": "cromo",
        "default": "figurita"
    },
    "mis_figus": {
        "AR": "Mis Figus",
        "UY": "Mis Figus",
        "MX": "Mis Estampas",
        "CL": "Mis Láminas",
        "CO": "Mis Láminas",
        "ES": "Mis Cromos",
        "default": "Mi Álbum"
    },
    "repes": {
        "AR": "repes",
        "UY": "repes",
        "MX": "repetidas",
        "CL": "repetidas",
        "CO": "repetidas",
        "ES": "repes",
        "default": "repetidas"
    }
    # app/translations.py

# ... (mantén lo que ya tenías) ...

    # --- NUEVAS TRADUCCIONES PARA ALBUM.HTML ---
    "mi_album": {
        "AR": "Mi Álbum", "UY": "Mi Álbum", "PE": "Mi Álbum",
        "MX": "Mi Álbum", "CL": "Mi Álbum", "CO": "Mi Álbum",
        "default": "Mi Álbum"
    },
    "compartir_figuritas": {
        "AR": "Compartir Figuritas", "UY": "Compartir Figuritas", "PE": "Compartir Figuritas",
        "MX": "Compartir Estampas", "CL": "Compartir Láminas", "CO": "Compartir Láminas",
        "default": "Compartir Figuritas"
    },
    "hora_de_canjear": {
        "AR": "¡Hora de Canjear!", "UY": "¡Hora de Canjear!", "PE": "¡Hora de Canjear!",
        "MX": "¡Hora de Intercambiar!", "CL": "¡Hora de Cambiar!", "CO": "¡Hora de Cambiar!",
        "default": "¡Hora de Intercambiar!"
    },
    "mensaje_hora_canjear": {
        "AR": "La mejor forma de conseguir figuritas rápido es avisarle a tus amigos qué te falta y qué tenés repetido. ¿Compartimos tu lista en WhatsApp?",
        "UY": "La mejor forma de conseguir figuritas rápido es avisarle a tus amigos qué te falta y qué tenés repetido. ¿Compartimos tu lista en WhatsApp?",
        "PE": "La mejor forma de conseguir figuritas rápido es avisarle a tus amigos qué te falta y qué tenés repetido. ¿Compartimos tu lista en WhatsApp?",
        "MX": "La mejor forma de conseguir estampas rápido es avisarle a tus amigos qué te falta y qué tienes repetido. ¿Compartimos tu lista en WhatsApp?",
        "CL": "La mejor forma de conseguir láminas rápido es avisarle a tus amigos qué te falta y qué tienes repetido. ¿Compartimos tu lista en WhatsApp?",
        "CO": "La mejor forma de conseguir láminas rápido es avisarle a tus amigos qué te falta y qué tienes repetido. ¿Compartimos tu lista en WhatsApp?",
        "default": "La mejor forma de conseguir figuritas rápido es avisarle a tus amigos qué te falta y qué tienes repetido. ¿Compartimos tu lista en WhatsApp?"
    },
    "mensaje_logro_wsp": {
        "AR": "¡Completé la página de",
        "UY": "¡Completé la página de",
        "PE": "¡Completé la página de",
        "MX": "¡Llené la página de",
        "CL": "¡Completé la página de",
        "CO": "¡Llené la página de",
        "default": "¡Completé la página de"
    },
    "mensaje_logro_wsp_2": {
        "AR": "! Sumate a Canje AlToque 26 para cambiar figuritas: https://canjealtoque26.com",
        "UY": "! Sumate a Canje AlToque 26 para cambiar figuritas: https://canjealtoque26.com",
        "PE": "! Únete a Canje AlToque 26 para cambiar figuritas: https://canjealtoque26.com",
        "MX": "! Únete a Canje AlToque 26 para intercambiar estampas: https://canjealtoque26.com",
        "CL": "! Súmate a Canje AlToque 26 para cambiar láminas: https://canjealtoque26.com",
        "CO": "! Únete a Canje AlToque 26 para cambiar láminas: https://canjealtoque26.com",
        "default": "! Únete a Canje AlToque 26 para intercambiar: https://canjealtoque26.com"
    },
    "texto_canvas_subtitulo": {
        "AR": "🏆 Álbum de Canje AlToque 26",
        "default": "🏆 Álbum de Canje AlToque 26"
    },
    "texto_canvas_cta": {
        "AR": "Armá tu álbum gratis e intercambiá en:",
        "UY": "Armá tu álbum gratis e intercambiá en:",
        "PE": "Arma tu álbum gratis e intercambia en:",
        "MX": "Arma tu álbum gratis e intercambia en:",
        "CL": "Arma tu álbum gratis e intercambia en:",
        "CO": "Arma tu álbum gratis e intercambia en:",
        "default": "Arma tu álbum gratis e intercambia en:"
    },
    "felicitaciones_modal": {
        "AR": "¡Felicitaciones! Tenés todas las figuritas de",
        "UY": "¡Felicitaciones! Tenés todas las figuritas de",
        "PE": "¡Felicitaciones! Tienes todas las figuritas de",
        "MX": "¡Felicidades! Tienes todas las estampas de",
        "CL": "¡Felicitaciones! Tienes todas las láminas de",
        "CO": "¡Felicitaciones! Tienes todas las láminas de",
        "default": "¡Felicidades! Tienes todas las figuritas de"
    }
}

def t(key: str, country_code: str = "AR") -> str:
    """
    Devuelve el término correcto según el país.
    Si el país no está configurado para esa palabra, usa el 'default' (Español Neutral).
    Si la palabra no existe en el diccionario, devuelve la misma key por seguridad.
    """
    # Si por alguna razón no llega el país (ej: usuario no logueado), usamos AR
    if not country_code:
        country_code = "AR"
        
    item = TRANSLATIONS.get(key)
    if not item:
        return key # Fallback: si te olvidás de agregarla, muestra el texto crudo y no rompe la app
    
    return item.get(country_code, item.get("default", key))
