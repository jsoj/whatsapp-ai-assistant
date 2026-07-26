import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse
from src.config import settings
from src.memory import init_db, add_message, get_recent_history
from src.gemini_service import generate_ai_response
from src.evolution_service import send_text_message

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

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "whatsapp-ai-assistant",
        "authorized_owners": settings.owner_numbers
    }

async def process_whatsapp_message(sender_number: str, message_text: str):
    """
    Processa a mensagem em segundo plano: salva no banco, consulta o Gemini e responde no WhatsApp.
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    
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
        
        # Ignora mensagens enviadas pelo próprio bot (fromMe == True)
        if key.get("fromMe") is True:
            return JSONResponse({"status": "ignored", "reason": "message_from_me"})

        remote_jid = key.get("remoteJid", "")
        sender_number = "".join(filter(str.isdigit, remote_jid.split("@")[0]))

        # Extrai o texto da mensagem (conversation ou extendedTextMessage)
        message = payload_data.get("message", {})
        message_text = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text") or
            ""
        )

        if not message_text:
            return JSONResponse({"status": "ignored", "reason": "no_text_content"})

        # Segurança: Verifica se o número remetente está na lista de números autorizados
        authorized = False
        for owner in settings.owner_numbers:
            if owner in sender_number or sender_number in owner:
                authorized = True
                break

        if not authorized:
            print(f"⚠️ [Security] Mensagem recebida de número não autorizado: {sender_number}")
            return JSONResponse({"status": "unauthorized", "reason": "number_not_in_owner_list"})

        print(f"📩 [Mensagem Recebida de {sender_number}]: {message_text}")

        # Processa em background para responder rapidamente ao webhook da Evolution API
        task = BackgroundTask(process_whatsapp_message, sender_number, message_text)
        return JSONResponse({"status": "processing", "sender": sender_number}, background=task)

    return JSONResponse({"status": "ignored", "event": event})
