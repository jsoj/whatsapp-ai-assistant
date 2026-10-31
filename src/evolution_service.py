import asyncio
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

async def fetch_media_base64(payload_or_key: dict) -> str | None:
    """
    Busca o áudio/mídia em Base64 através da Evolution API.
    """
    url = f"{settings.EVOLUTION_URL}/chat/getBase64FromMediaMessage/{settings.EVOLUTION_INSTANCE}"
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }
    
    # Prepara a mensagem conforme o formato enviado (objeto data completo ou dict key)
    msg_obj = payload_or_key if "key" in payload_or_key and "message" in payload_or_key else {"key": payload_or_key}
    payload = {
        "message": msg_obj,
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
                # Tentativa de fallback com payload simples
                fallback_payload = {"message": {"key": payload_or_key.get("key", payload_or_key)}}
                resp_fb = await client.post(url, json=fallback_payload, headers=headers)
                if resp_fb.status_code in [200, 201]:
                    data_fb = resp_fb.json()
                    return data_fb.get("base64") or data_fb.get("media")
    except Exception as e:
        print(f"❌ [Evolution Media Exception]: {e}")
    return None

async def send_audio_message(phone_number: str, text: str, voice: str = "pt-BR-FranciscaNeural") -> bool:
    """
    Converte texto em áudio via Edge-TTS (Vozes Neurais Microsoft) e envia como mensagem de voz no WhatsApp.
    Voz padrão: pt-BR-FranciscaNeural (Feminina expressiva)
    """
    import re
    import base64
    import edge_tts

    cleaned_number = "".join(filter(str.isdigit, phone_number))
    url = f"{settings.EVOLUTION_URL}/message/sendWhatsAppAudio/{settings.EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }

    # Limpeza refinada de Markdown para fala natural
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    clean = re.sub(r'[*_#`~>|-]', ' ', clean)
    clean = re.sub(r'https?://\S+', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    if len(clean) > 1200:
        clean = clean[:1200] + "..."

    try:
        communicate = edge_tts.Communicate(clean, voice)
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if not audio_data:
            print("⚠️ [Edge-TTS] Nenhum dado de áudio retornado.")
            return False

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        payload = {
            "number": cleaned_number,
            "audio": audio_base64,
            "encoding": True
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                res_data = resp.json()
                msg_id = res_data.get("key", {}).get("id")
                if msg_id:
                    register_bot_message_id(msg_id)
                print(f"🎙️ [Evolution API] Áudio Edge-TTS ({voice}) enviado com sucesso para {cleaned_number} (ID: {msg_id})")
                return True
            else:
                print(f"❌ [Evolution Audio Error] Status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        print(f"❌ [Evolution Audio Exception]: {e}")
        return False

async def send_presence(phone_number: str, presence: str = "composing") -> bool:
    """
    Envia indicador de presença ('composing' ou 'recording') no chat do WhatsApp.
    """
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    url = f"{settings.EVOLUTION_URL}/chat/sendPresence/{settings.EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }

    payload = {
        "number": cleaned_number,
        "presence": presence,
        "delay": 1200
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code in [200, 201]
    except Exception as e:
        print(f"⚠️ [Evolution Presence Exception]: {e}")
        return False

async def send_reaction(message_key: dict, reaction: str = "🤖") -> bool:
    """
    Envia uma reação de emoji para a mensagem do usuário no WhatsApp.
    """
    if not message_key:
        return False

    url = f"{settings.EVOLUTION_URL}/message/sendReaction/{settings.EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": settings.EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }

    payload = {
        "key": message_key,
        "reaction": reaction
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code in [200, 201]
    except Exception as e:
        print(f"⚠️ [Evolution Reaction Exception]: {e}")
        return False

