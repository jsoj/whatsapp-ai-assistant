import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse
from src.config import settings
from src.memory import init_db, add_message, get_recent_history
from src.gemini_service import generate_ai_response, generate_ai_response_from_audio
from src.antigravity_service import run_antigravity_agent, transcribe_audio
from src.evolution_service import (
    send_text_message,
    fetch_media_base64,
    send_audio_message,
    send_presence,
    send_reaction
)
from src.bot_state import is_bot_message

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"🚀 [WhatsApp AI Assistant] Inicializado na porta {settings.PORT}")
    print(f"📌 [Config] Evolution URL: {settings.EVOLUTION_URL}")
    print(f"📌 [Config] Números autorizados: {settings.owner_numbers}")
    print(f"🤖 [Config] Antigravity Motor Ativo: {settings.USE_ANTIGRAVITY_AGENT}")
    yield

app = FastAPI(
    title="WhatsApp AI Assistant (Antigravity Engine)",
    description="Microserviço integrando Evolution API e o Agente Antigravity com acesso total ao contexto da VPS",
    version="2.0.0",
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
        "engine": "antigravity-agent" if settings.USE_ANTIGRAVITY_AGENT else "gemini-direct",
        "authorized_owners": settings.owner_numbers
    }

async def process_whatsapp_message(sender_number: str, message_text: str, message_key: dict = None):
    """
    Processa a mensagem de texto:
    1. Envia status 'digitando...' e reação 🤖 no WhatsApp
    2. Executa a instrução no motor do Antigravity (com histórico e ferramentas)
    3. Salva no banco de dados
    4. Envia resposta de volta e atualiza reação para ✅
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        # Indicadores imediatos no WhatsApp
        await send_presence(cleaned_sender, "composing")
        if message_key:
            await send_reaction(message_key, "🤖")

        # Salva mensagem do usuário no banco
        add_message(cleaned_sender, "user", message_text)

        if settings.USE_ANTIGRAVITY_AGENT:
            # Executa com o motor completo do Antigravity CLI
            ai_response = await run_antigravity_agent(cleaned_sender, message_text)
        else:
            # Fallback direto SDK Gemini
            history = get_recent_history(cleaned_sender, limit=14)
            ai_response = generate_ai_response(cleaned_sender, message_text, history)

        # Salva a resposta da IA no banco
        add_message(cleaned_sender, "model", ai_response)

        # Envia a resposta de volta ao WhatsApp via Evolution API
        await send_text_message(cleaned_sender, ai_response)

        # Atualiza a reação para indicar conclusão
        if message_key:
            await send_reaction(message_key, "✅")

    except Exception as e:
        print(f"❌ [Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro no processamento: {e}")
        if message_key:
            await send_reaction(message_key, "❌")

async def process_whatsapp_audio(sender_number: str, payload_data: dict, mimetype: str, message_key: dict = None):
    """
    Processa mensagem de áudio:
    1. Baixa o áudio via Evolution API
    2. Transcreve o áudio com Gemini Multimodal
    3. Envia o texto resultante para o motor Antigravity
    4. Responde em texto (e opcionalmente áudio) no WhatsApp
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        await send_presence(cleaned_sender, "recording")
        if message_key:
            await send_reaction(message_key, "🎙️")

        # 1. Baixa o conteúdo Base64 do áudio
        audio_base64 = await fetch_media_base64(payload_data)
        
        if not audio_base64:
            print(f"⚠️ [Audio Download Warning] Não foi possível baixar áudio de {cleaned_sender}")
            await send_text_message(cleaned_sender, "Recebi seu áudio, mas não consegui realizar o download para transcrição. Por favor, tente enviar em texto.")
            return

        # 2. Transcrição do áudio
        transcription = transcribe_audio(audio_base64, mimetype)
        if transcription:
            print(f"📝 [Transcrição Áudio de {cleaned_sender}]: {transcription}")
            prompt_text = f"[Mensagem de Áudio Transcrita]: {transcription}"
        else:
            prompt_text = "Processe o áudio enviado pelo usuário e execute as tarefas solicitadas."

        add_message(cleaned_sender, "user", f"[Áudio]: {transcription or 'Áudio recebido'}")

        # 3. Execução no Antigravity
        if settings.USE_ANTIGRAVITY_AGENT:
            ai_response = await run_antigravity_agent(cleaned_sender, prompt_text)
        else:
            ai_response = generate_ai_response_from_audio(cleaned_sender, audio_base64, mimetype)

        add_message(cleaned_sender, "model", ai_response)

        # 4. Envia resposta em ÁUDIO DE VOZ (se disponível)
        try:
            await send_audio_message(cleaned_sender, ai_response)
        except Exception as audio_err:
            print(f"⚠️ [Audio Send Warning]: {audio_err}")

        # 5. Envia resposta em TEXTO no WhatsApp
        await send_text_message(cleaned_sender, ai_response)

        if message_key:
            await send_reaction(message_key, "✅")

    except Exception as e:
        print(f"❌ [Audio Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro ao processar seu áudio: {e}")
        if message_key:
            await send_reaction(message_key, "❌")

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
            task = BackgroundTask(process_whatsapp_audio, sender_number, payload_data, mimetype, key)
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
        task = BackgroundTask(process_whatsapp_message, sender_number, message_text, key)
        return JSONResponse({"status": "processing", "sender": sender_number}, background=task)

    return JSONResponse({"status": "ignored", "event": event})
