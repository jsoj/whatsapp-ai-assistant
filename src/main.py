import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse
from src.config import settings
from src.memory import init_db, add_message, get_recent_history
from src.gemini_service import generate_ai_response, generate_ai_response_from_audio
from src.evolution_service import send_text_message, fetch_media_base64
from src.bot_state import is_bot_message

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"🚀 [WhatsApp AI Assistant] Inicializado na porta {settings.PORT}")
    print(f"📌 [Config] Evolution URL: {settings.EVOLUTION_URL}")
    print(f"📌 [Config] Números autorizados: {settings.owner_numbers}")
    yield

app = FastAPI(
    title="WhatsApp AI Assistant",
    description="Microserviço integrando Evolution API e Gemini API com o contexto global do projeto",
    version="1.0.0",
    lifespan=lifespan
)

# Inicializa o DB ao carregar a aplicação
init_db()

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "whatsapp-ai-assistant",
        "authorized_owners": settings.owner_numbers
    }

async def process_whatsapp_message(sender_number: str, message_text: str):
    """
    Processa a mensagem de texto em segundo plano: salva no banco, consulta o Gemini e responde no WhatsApp.
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        # 1. Salva mensagem do usuário no banco
        add_message(cleaned_sender, "user", message_text)

        # 2. Busca histórico recente da conversa
        history = get_recent_history(cleaned_sender, limit=14)

        # 3. Gera resposta inteligente com o Gemini (carregando contexto AGENTS.md)
        ai_response = generate_ai_response(cleaned_sender, message_text, history)

        # 4. Salva a resposta da IA no banco
        add_message(cleaned_sender, "model", ai_response)

        # 5. Envia a resposta de volta ao WhatsApp via Evolution API
        await send_text_message(cleaned_sender, ai_response)
    except Exception as e:
        print(f"❌ [Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro interno no processamento: {e}")

async def process_whatsapp_audio(sender_number: str, message_key: dict, mimetype: str):
    """
    Processa mensagem de áudio em segundo plano: baixa o áudio, envia ao Gemini multimodal e responde em áudio e texto.
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        # 1. Busca o conteúdo Base64 do áudio na Evolution API
        audio_base64 = await fetch_media_base64(message_key)
        
        if not audio_base64:
            ai_response = "Recebi seu áudio, mas não foi possível fazer o download para transcrição."
        else:
            # 2. Processa áudio no Gemini 2.5 Flash
            ai_response = generate_ai_response_from_audio(cleaned_sender, audio_base64, mimetype)

        # 3. Salva no histórico
        add_message(cleaned_sender, "user", "[Mensagem de Áudio]")
        add_message(cleaned_sender, "model", ai_response)

        # 4. Envia resposta em ÁUDIO DE VOZ e TEXTO no WhatsApp
        await send_audio_message(cleaned_sender, ai_response)
        await send_text_message(cleaned_sender, ai_response)
    except Exception as e:
        print(f"❌ [Audio Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro ao processar seu áudio: {e}")

@app.post("/webhook/evolution")
async def webhook_evolution(request: Request):
    """
    Endpoint HTTP Webhook para receber mensagens da Evolution API.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event = data.get("event")
    
    # Processa eventos de mensagens novas (messages.upsert ou SEND_MESSAGE)
    if event in ["messages.upsert", "SEND_MESSAGE"]:
        payload_data = data.get("data", {})
        key = payload_data.get("key", {})
        msg_id = key.get("id", "")

        # Ignora mensagens geradas pela própria resposta da IA
        if is_bot_message(msg_id):
            return JSONResponse({"status": "ignored", "reason": "bot_own_message"})

        remote_jid = key.get("remoteJid", "")
        sender_number = "".join(filter(str.isdigit, remote_jid.split("@")[0]))

        # Se fromMe == True (ex: enviando mensagem para si mesmo no WhatsApp)
        # só aceita se o número do remetente for um dono autorizado
        if key.get("fromMe") is True:
            is_owner = any(owner in sender_number or sender_number in owner for owner in settings.owner_numbers)
            if not is_owner:
                return JSONResponse({"status": "ignored", "reason": "message_from_me"})

        # Segurança: Verifica se o número remetente está na lista de números autorizados
        authorized = any(owner in sender_number or sender_number in owner for owner in settings.owner_numbers)
        if not authorized:
            print(f"⚠️ [Security] Mensagem recebida de número não autorizado: {sender_number}")
            return JSONResponse({"status": "unauthorized", "reason": "number_not_in_owner_list"})

        message = payload_data.get("message", {})

        # Verifica se é mensagem de áudio (audioMessage)
        audio_msg = message.get("audioMessage")
        if audio_msg:
            raw_mime = audio_msg.get("mimetype", "audio/ogg")
            mimetype = raw_mime.split(";")[0]
            print(f"🎙️ [Áudio Recebido de {sender_number}]: formato {mimetype}")
            task = BackgroundTask(process_whatsapp_audio, sender_number, key, mimetype)
            return JSONResponse({"status": "processing_audio", "sender": sender_number}, background=task)

        # Extrai o texto da mensagem (conversation ou extendedTextMessage)
        message_text = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text") or
            ""
        )

        if not message_text:
            return JSONResponse({"status": "ignored", "reason": "no_supported_content"})

        print(f"📩 [Mensagem Recebida de {sender_number}]: {message_text}")

        # Processa texto em background
        task = BackgroundTask(process_whatsapp_message, sender_number, message_text)
        return JSONResponse({"status": "processing", "sender": sender_number}, background=task)

    return JSONResponse({"status": "ignored", "event": event})
