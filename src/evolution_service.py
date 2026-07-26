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

async def fetch_media_base64(message_key: dict) -> str | None:
    """
    Busca o áudio/mídia em Base64 através da Evolution API.
    """
    url = f"{settings.EVOLUTION_URL}/chat/getBase64FromMediaMessage/{settings.EVOLUTION_INSTANCE}"
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }
    payload = {
        "message": {
            "key": message_key
        },
        "convertToMp3": False
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                data = resp.json()
                return data.get("base64") or data.get("media")
            else:
                print(f"❌ [Evolution Media Error] Status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ [Evolution Media Exception]: {e}")
    return None

async def send_audio_message(phone_number: str, text: str) -> bool:
    """
    Converte texto em áudio via gTTS e envia como mensagem de voz no WhatsApp via Evolution API.
    """
    from io import BytesIO
    import base64
    from gtts import gTTS

    cleaned_number = "".join(filter(str.isdigit, phone_number))
    url = f"{settings.EVOLUTION_URL}/message/sendWhatsAppAudio/{settings.EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }

    try:
        # Limpa formatação markdown para leitura fluida da voz
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace("_", "")
        tts = gTTS(text=clean_text, lang='pt', tld='com.br')
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        audio_base64 = base64.b64encode(mp3_fp.read()).decode('utf-8')
        audio_data_uri = f"data:audio/mp3;base64,{audio_base64}"

        payload = {
            "number": cleaned_number,
            "audio": audio_data_uri,
            "delay": 1000
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                msg_id = res_data.get("key", {}).get("id")
                if msg_id:
                    register_bot_message_id(msg_id)
                print(f"🎙️ [Evolution API] Áudio de resposta enviado com sucesso para {cleaned_number}")
                return True
            else:
                print(f"❌ [Evolution Audio Error] Status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        print(f"❌ [Evolution Audio Exception]: {e}")
        return False
