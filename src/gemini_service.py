import os
import time
import base64
from google import genai
from google.genai import types
from src.config import settings
from src.context_loader import load_agents_context
from src.tools import AVAILABLE_TOOLS, get_tools_for_request

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro"
]

AUDIO_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro"
]

def get_client() -> genai.Client:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)

def _build_chat_history(history: list[dict] | None) -> list[types.Content]:
    """Converte o histórico do SQLite para o formato types.Content do SDK google-genai."""
    if not history:
        return []
    formatted = []
    for item in history:
        role = "model" if item.get("role") == "model" else "user"
        text = (item.get("content") or "").strip()
        if text:
            formatted.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    return formatted

def generate_ai_response(
    phone_number: str,
    user_text: str,
    history: list[dict] = None,
    custom_system_instruction: str = None,
    sender_digits: str = None
) -> str:
    """
    Gera uma resposta rápida (~1.5s-2.5s) com suporte a Function Calling autônomo,
    histórico de conversa e Fallback automático de modelos.
    Aplica RBAC em tools baseado em sender_digits e phone_number.
    """
    client = get_client()
    system_instruction = custom_system_instruction or load_agents_context()
    primary_model = settings.GEMINI_MODEL or "gemini-2.5-flash"
    if primary_model == "gemini-3.6-flash":
        primary_model = "gemini-2.5-flash"

    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]

    # Ferramentas filtradas por privilégios RBAC
    caller_digits = sender_digits or phone_number
    active_tools = get_tools_for_request(phone_number, caller_digits)

    # Se o último item do history já for a mensagem atual do usuário, remove para não duplicar
    clean_history = list(history or [])
    if clean_history and clean_history[-1].get("role") == "user" and clean_history[-1].get("content") == user_text:
        clean_history = clean_history[:-1]
    formatted_history = _build_chat_history(clean_history)

    last_error = None
    for model_name in models_to_try:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=active_tools if active_tools else None,
                temperature=0.4,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )

            chat = client.chats.create(
                model=model_name,
                config=config,
                history=formatted_history
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
                time.sleep(0.5)
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

    prompt = "Ouça atenciosamente este áudio do usuário, compreenda a solicitação, execute todas as ações solicitadas (ex: notas no Cofre, gastos, trilho de foco, e-mails, comandos) e responda em português."

    last_error = None
    for model_name in AUDIO_MODELS:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=AVAILABLE_TOOLS,
                temperature=0.4,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
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
                time.sleep(0.5)
                continue
            else:
                break

    return f"⚠️ Ocorreu um erro ao processar seu áudio: {last_error}"

def generate_ai_response_from_media(
    phone_number: str,
    media_base64: str,
    mime_type: str,
    caption: str = "",
    file_name: str = "",
    history: list[dict] = None,
    custom_system_instruction: str = None,
    default_tag: str = ""
) -> str:
    """
    Processa imagens (comprovantes, recibos, prints, fotos) e documentos (PDF, TXT, CSV)
    com Gemini 2.5 Flash Multimodal e acesso às ferramentas do Cofre e VPS.
    """
    client = get_client()
    system_instruction = custom_system_instruction or load_agents_context()
    raw_bytes = base64.b64decode(media_base64)
    clean_mime = (mime_type or "image/jpeg").split(";")[0].strip()

    media_part = types.Part.from_bytes(
        data=raw_bytes,
        mime_type=clean_mime
    )

    tag_instruction = f" IMPORTANTE: Ao registrar gasto no Cofre, passe sempre o parâmetro tag='{default_tag}'." if default_tag else ""

    if caption and caption.strip():
        prompt = (
            f"O usuário enviou este arquivo/imagem ({file_name or clean_mime}) com a seguinte instrução: '{caption.strip()}'.\n"
            "Analise o conteúdo visual/textual com precisão, execute as ferramentas necessárias "
            "(como registrar_gasto_pessoal se for um comprovante/recibo solicitado, ou atualizar notas no Cofre) "
            f"e responda de forma estruturada e objetiva no WhatsApp.{tag_instruction}"
        )
    else:
        prompt = (
            f"O usuário enviou este arquivo/imagem ({file_name or clean_mime}) sem legenda.\n"
            "1. Analise detalhadamente o conteúdo (se for comprovante PIX/boleto/nota fiscal/recibo, extraia Data, Beneficiário, Categoria sugerida, Valor e Forma de Pagamento e lance usando registrar_gasto_pessoal).\n"
            f"2. Confirme o que foi lançado de forma clara e amigável.{tag_instruction}"
        )

    formatted_history = _build_chat_history(history)
    last_error = None

    for model_name in AUDIO_MODELS:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=AVAILABLE_TOOLS,
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
            chat = client.chats.create(
                model=model_name,
                config=config,
                history=formatted_history
            )
            response = chat.send_message([media_part, prompt])
            if response and response.text:
                return response.text.strip()
            return "Mídia analisada e processada com sucesso."
        except Exception as e:
            err_str = str(e)
            print(f"⚠️ [Gemini Media Error] Modelo {model_name} falhou: {err_str[:200]}")
            last_error = e
            if "429" in err_str or "404" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                time.sleep(0.5)
                continue
            break

    return f"⚠️ Ocorreu um erro ao analisar a imagem/documento: {last_error}"

