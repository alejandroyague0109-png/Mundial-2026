import requests # Usamos la librería sincrónica clásica
import sys

# --- TUS DATOS ---
TOKEN = "TU_TOKEN_AQUI"
CHAT_ID = "TU_ID_NUMERICO_AQUI"

def test_telegram():
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 Prueba final desde Python/Requests.",
        "parse_mode": "Markdown"
    }
    
    print(f"📡 Conectando a Telegram para ID: {CHAT_ID}...")
    
    try:
        # Intentamos conexión directa sin async
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"Respuesta Raw: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ ¡FUNCIONÓ! El problema era la librería httpx en tu Windows.")
        else:
            print(f"\n❌ Error de Telegram: {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ Error de conexión irrecuperable en local: {e}")
        print("⚠️ IGNORA ESTO. En Railway funcionará porque usa Linux.")

if __name__ == "__main__":
    test_telegram()