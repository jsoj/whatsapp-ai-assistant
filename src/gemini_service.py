import os
import google.generativeai as genai
from src.config import settings
from src.context_loader import load_agents_context

def init_gemini():
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)

def generate_ai_response(phone_number: str, user_text: str, history: list[dict]) -> str:
    """
    Gera uma resposta do Gemini considerando o contexto global e o histórico de mensagens.
    """
    init_gemini()
    system_instruction = load_agents_context()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

    try:
        # Tenta utilizar a biblioteca google-generativeai
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )

        formatted_history = []
        for msg in history[:-1]:  # inclui o histórico anterior exceto a última que acabamos de receber
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_text)
        return response.text.strip()
    except Exception as e:
        print(f"[Gemini Error] Erro ao chamar o modelo {model_name}: {e}")
        # Tenta fallback para gemini-1.5-flash se gemini-2.5-flash der erro
        if model_name != "gemini-1.5-flash":
            try:
                fallback_model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    system_instruction=system_instruction
                )
                response = fallback_model.generate_content(user_text)
                return response.text.strip()
            except Exception as e_fallback:
                print(f"[Gemini Fallback Error]: {e_fallback}")
        return f"Desculpe, ocorreu um erro ao consultar o Gemini: {e}"
