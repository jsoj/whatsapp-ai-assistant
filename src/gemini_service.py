import os
import base64
from google import genai
from google.genai import types
from src.config import settings
from src.context_loader import load_agents_context
from src.tools import AVAILABLE_TOOLS

def get_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)

def generate_ai_response(phone_number: str, user_text: str, history: list[dict]) -> str:
    """
    Gera uma resposta inteligente do Gemini 2.5 Flash com suporte nativo a Function Calling autônomo.
    """
    client = get_client()
    system_instruction = load_agents_context()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

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
        return response.text.strip() if response.text else "Ação executada com sucesso."
    except Exception as e:
        print(f"[Gemini Error] Erro ao consultar o modelo {model_name}: {e}")
        return f"Desculpe, ocorreu um erro ao consultar o Gemini: {e}"

def generate_ai_response_from_audio(phone_number: str, audio_base64: str, mime_type: str = "audio/ogg") -> str:
    """
    Processa uma mensagem de áudio enviada ao Gemini 2.5 Flash, executa ferramentas autonomamente e gera a resposta.
    """
    client = get_client()
    system_instruction = load_agents_context()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    try:
        raw_bytes = base64.b64decode(audio_base64)
        audio_part = types.Part.from_bytes(
            data=raw_bytes,
            mime_type=mime_type or "audio/ogg"
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=AVAILABLE_TOOLS,
            temperature=0.7
        )

        prompt = "Ouça atenciosamente este áudio do usuário, compreenda a solicitação, execute todas as ações solicitadas (ex: e-mails, comandos, deploys) e responda em português."

        chat = client.chats.create(
            model=model_name,
            config=config
        )

        response = chat.send_message([audio_part, prompt])
        return response.text.strip() if response.text else "Áudio processado e ação executada com sucesso."
    except Exception as e:
        print(f"[Gemini Audio Error]: {e}")
        return f"Desculpe, ocorreu um erro ao processar seu áudio: {e}"
