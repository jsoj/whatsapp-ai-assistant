import os
import base64
import google.generativeai as genai
from src.config import settings
from src.context_loader import load_agents_context
from src.tools import AVAILABLE_TOOLS, send_email, execute_command, deploy_coolify_application

def init_gemini():
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)

def run_tool_call(fn_name: str, fn_args: dict) -> str:
    print(f"⚡ [Tool Call] Executando função autônoma '{fn_name}' com argumentos: {fn_args}")
    if fn_name == "send_email":
        return send_email(**fn_args)
    elif fn_name == "execute_command":
        return execute_command(**fn_args)
    elif fn_name == "deploy_coolify_application":
        return deploy_coolify_application(**fn_args)
    return f"Ferramenta {fn_name} desconhecida."

def generate_ai_response(phone_number: str, user_text: str, history: list[dict]) -> str:
    """
    Gera uma resposta do Gemini considerando o contexto global, histórico e executando ferramentas autonomamente.
    """
    init_gemini()
    system_instruction = load_agents_context()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=AVAILABLE_TOOLS
        )

        formatted_history = []
        for msg in history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_text)

        # Loop de execução autônoma de ferramentas
        for _ in range(5):
            candidate = response.candidates[0] if (response and response.candidates) else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break
            
            function_call = None
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    function_call = part.function_call
                    break
            
            if not function_call:
                break

            fn_name = function_call.name
            fn_args = dict(function_call.args)
            tool_result = run_tool_call(fn_name, fn_args)

            response = chat.send_message(
                genai.types.Part.from_function_response(
                    name=fn_name,
                    response={"result": tool_result}
                )
            )

        return response.text.strip() if (response and response.text) else "Ação executada com sucesso."
    except Exception as e:
        print(f"[Gemini Error] Erro ao chamar o modelo {model_name}: {e}")
        return f"Desculpe, ocorreu um erro ao consultar o Gemini: {e}"

def generate_ai_response_from_audio(phone_number: str, audio_base64: str, mime_type: str = "audio/ogg") -> str:
    """
    Processa uma mensagem de áudio enviada ao Gemini 2.5 Flash, transcreve, executa ferramentas e gera a resposta.
    """
    init_gemini()
    system_instruction = load_agents_context()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    try:
        raw_bytes = base64.b64decode(audio_base64)
        audio_part = {
            "mime_type": mime_type or "audio/ogg",
            "data": raw_bytes
        }

        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=AVAILABLE_TOOLS
        )
        prompt = "Ouça atenciosamente este áudio do usuário, compreenda a solicitação, execute as ferramentas necessárias se solicitado (ex: enviar e-mail, comandos) e responda em português."
        
        chat = model.start_chat()
        response = chat.send_message([audio_part, prompt])

        # Loop de execução autônoma de ferramentas para áudio
        for _ in range(5):
            candidate = response.candidates[0] if (response and response.candidates) else None
            if not candidate or not candidate.content or not candidate.content.parts:
                break
            
            function_call = None
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call and part.function_call.name:
                    function_call = part.function_call
                    break
            
            if not function_call:
                break

            fn_name = function_call.name
            fn_args = dict(function_call.args)
            tool_result = run_tool_call(fn_name, fn_args)

            response = chat.send_message(
                genai.types.Part.from_function_response(
                    name=fn_name,
                    response={"result": tool_result}
                )
            )

        return response.text.strip() if (response and response.text) else "Áudio processado e ação executada com sucesso."
    except Exception as e:
        print(f"[Gemini Audio Error]: {e}")
        return f"Desculpe, ocorreu um erro ao processar seu áudio: {e}"
