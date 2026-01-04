import re
import bcrypt

def hash_password(password):
    """Encripta la contraseña"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_text, hashed_text):
    """Verifica la contraseña"""
    try: 
        return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_text.encode('utf-8'))
    except: 
        return False

def limpiar_telefono(phone_input):
    """Quita guiones y espacios"""
    if not phone_input: return ""
    return re.sub(r"\D", "", phone_input)

def validar_formato_telefono(phone_clean):
    """Verifica longitud de 10 a 14 dígitos"""
    return bool(re.match(r"^\d{10,14}$", phone_clean))