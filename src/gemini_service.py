import os
import time
import base64
from google import genai
from google.genai import types
from src.config import settings
from src.context_loader import load_agents_context
from src.tools import AVAILABLE_TOOLS

FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.0-flash"
]

AUDIO_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro"
]

def get_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

def generate_ai_response(phone_number: str, user_text: str, history: list[dict]) -> str:
    """
    Gera uma resposta inteligente com suporte a Function Calling autônomo e Fallback automático de modelos.
    """
    client = get_client()
    system_instruction = load_agents_context()
    primary_model = settings.GEMINI_MODEL or "gemini-3.6-flash"
    
    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    last_error = None
    for model_name in models_to_try:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=AVAILABLE_TOOLS,
                temperature=0.7
            )

            chat = client.chats.create(
                model=model_name,
                config=config
            )

            response = chat.send_message(user_text)
            if response and response.text:
                return response.text.strip()
            return "Ação executada com sucesso."
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [Gemini Error] Modelo {model_name} falhou: {err_str[:200]}")
            last_error = e
            if "429" in err_str or "404" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower() or "NOT_FOUND" in err_str:
                print(f"🔄 Modelo {model_name} indisponível (Erro 429/404). Tentando próximo modelo da lista...")
                time.sleep(1)
                continue
            else:
                break

    return f"⚠️ Erro ao consultar a API do Gemini: {last_error}"

def generate_ai_response_from_audio(phone_number: str, audio_base64: str, mime_type: str = "audio/ogg") -> str:
    """
    Processa mensagens de áudio com fallback automático de modelos Gemini multimodal.
    """
    client = get_client()
    system_instruction = load_agents_context()

    raw_bytes = base64.b64decode(audio_base64)
    audio_part = types.Part.from_bytes(
        data=raw_bytes,
        mime_type=mime_type or "audio/ogg"
    )

    prompt = "Ouça atenciosamente este áudio do usuário, compreenda a solicitação, execute todas as ações solicitadas (ex: e-mails, comandos, deploys) e responda em português."

    last_error = None
    for model_name in AUDIO_MODELS:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=AVAILABLE_TOOLS,
                temperature=0.7
            )

            chat = client.chats.create(
                model=model_name,
                config=config
            )

            response = chat.send_message([audio_part, prompt])
            if response and response.text:
                return response.text.strip()
            return "Áudio processado e ação executada com sucesso."
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [Gemini Audio Error] Modelo {model_name} falhou: {err_str[:200]}")
            last_error = e
            if "429" in err_str or "404" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower() or "NOT_FOUND" in err_str:
                print(f"🔄 Modelo {model_name} indisponível para áudio. Tentando próximo modelo...")
                time.sleep(1)
                continue
            else:
                break

    return f"⚠️ Ocorreu um erro ao processar seu áudio: {last_error}"
