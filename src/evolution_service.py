import httpx
import json
from src.config import settings
from src.bot_state import register_bot_message_id

async def send_text_message(phone_number: str, text: str) -> bool:
    """
    Envia uma mensagem de texto pelo WhatsApp através da Evolution API.
    """
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    url = f"{settings.EVOLUTION_URL}/message/sendText/{settings.EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }

    payload = {
        "number": cleaned_number,
        "text": text
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                msg_id = res_data.get("key", {}).get("id")
                if msg_id:
                    register_bot_message_id(msg_id)
                print(f"✅ [Evolution API] Mensagem enviada com sucesso para {cleaned_number} (ID: {msg_id})")
                return True
            else:
                print(f"❌ [Evolution API Error] Status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        print(f"❌ [Evolution API Exception]: {e}")
        return False
