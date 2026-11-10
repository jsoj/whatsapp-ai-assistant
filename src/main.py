import os
import asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse, HTMLResponse
from src.config import settings
from src.memory import init_db, add_message, get_recent_history
from src.gemini_service import (
    generate_ai_response,
    generate_ai_response_from_audio,
    generate_ai_response_from_media,
)
from src.antigravity_service import (
    run_antigravity_agent,
    route_and_execute,
    should_send_audio,
    transcribe_audio,
)
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
    print(f"🚀 [WhatsApp AI Assistant 2.5] Inicializado na porta {settings.PORT}")
    print(f"📌 [Config] Evolution URL: {settings.EVOLUTION_URL}")
    print(f"📌 [Config] Números autorizados: {settings.owner_numbers}")
    print(f"🤖 [Config] Antigravity Motor Ativo: {settings.USE_ANTIGRAVITY_AGENT}")
    yield

app = FastAPI(
    title="WhatsApp AI Assistant (Antigravity Hybrid Engine)",
    description="Microserviço integrando Evolution API, Fast-Path Gemini 2.5 Flash + Tools e Agente Antigravity com acesso total ao Cofre e VPS",
    version="2.5.0",
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
        "version": "2.5.0",
        "engine": "antigravity-agent" if settings.USE_ANTIGRAVITY_AGENT else "gemini-direct",
        "authorized_owners": settings.owner_numbers
    }

@app.get("/qrcode", response_class=HTMLResponse)
async def qrcode_page():
    """Página de reconexão do WhatsApp via QR Code com auto-refresh."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.EVOLUTION_URL}/instance/connect/{settings.EVOLUTION_INSTANCE}",
                headers={"apikey": settings.EVOLUTION_APIKEY}
            )
            data = resp.json()
            status_resp = await client.get(
                f"{settings.EVOLUTION_URL}/instance/connectionState/{settings.EVOLUTION_INSTANCE}",
                headers={"apikey": settings.EVOLUTION_APIKEY}
            )
            status_data = status_resp.json()
    except Exception as e:
        return HTMLResponse(f"<h3>Erro ao consultar Evolution API: {e}</h3>", status_code=500)

    state = status_data.get("instance", {}).get("state", "desconhecido")
    base64_img = data.get("base64", "")

    if state == "open":
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AURA ✨ Conectada</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
                .card { background: #1e293b; padding: 2.5rem; border-radius: 1rem; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
                h1 { color: #10b981; margin-bottom: 0.5rem; }
                p { color: #94a3b8; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✅ AURA ✨ Conectada!</h1>
                <p>O WhatsApp está conectado e pronto para responder no canal oficial.</p>
            </div>
        </body>
        </html>
        """)

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reconectar AURA ✨</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="15">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; padding: 1rem; }}
            .card {{ background: #1e293b; padding: 2rem; border-radius: 1.25rem; text-align: center; max-width: 420px; width: 100%; box-shadow: 0 20px 30px rgba(0,0,0,0.4); border: 1px solid #334155; }}
            h1 {{ font-size: 1.5rem; margin-top: 0; color: #38bdf8; }}
            .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; background: #dc2626; color: white; font-size: 0.85rem; font-weight: 600; margin-bottom: 1rem; }}
            .qr-box {{ background: white; padding: 1rem; border-radius: 1rem; display: inline-block; margin: 1rem 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
            img {{ width: 260px; height: 260px; display: block; }}
            ol {{ text-align: left; padding-left: 1.25rem; color: #cbd5e1; font-size: 0.95rem; line-height: 1.5; }}
            .refresh-note {{ color: #94a3b8; font-size: 0.8rem; margin-top: 1rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">Status: {state.upper()}</span>
            <h1>Reconectar AURA ✨</h1>
            <p style="color: #94a3b8; font-size: 0.9rem;">Escaneie o QR Code abaixo com o WhatsApp do seu celular:</p>
            <div class="qr-box">
                <img src="{base64_img}" alt="QR Code WhatsApp" />
            </div>
            <ol>
                <li>Abra o <strong>WhatsApp</strong> no celular</li>
                <li>Toque em <strong>Aparelhos Conectados</strong></li>
                <li>Selecione <strong>Conectar um aparelho</strong></li>
                <li>Aponte a câmera para o QR Code acima</li>
            </ol>
            <p class="refresh-note">🔄 Esta página atualiza automaticamente a cada 15 segundos se expirar.</p>
        </div>
    </body>
    </html>
    """)

async def process_whatsapp_message(
    sender_number: str,
    message_text: str,
    message_key: dict = None,
    sender_digits: str = None
):
    """
    Processa a mensagem de texto:
    1. Envia status 'digitando...' e reação ⚡ no WhatsApp
    2. Executa no Roteador Híbrido com RBAC de ferramentas por participante
    3. Salva no banco de dados
    4. Envia resposta em texto (e áudio inteligente se aplicável) e atualiza reação para ✅
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        # Indicadores imediatos no WhatsApp
        await send_presence(cleaned_sender, "composing")
        if message_key:
            await send_reaction(message_key, "⚡")

        # Obtém histórico recente antes de gravar a nova mensagem
        history = get_recent_history(cleaned_sender, limit=14)
        add_message(cleaned_sender, "user", message_text)

        # Executa pelo Roteador Inteligente Híbrido com RBAC do emissor
        caller_digits = sender_digits or cleaned_sender
        ai_response = await route_and_execute(
            cleaned_sender,
            message_text,
            history,
            sender_digits=caller_digits
        )

        # Salva a resposta da IA no banco
        add_message(cleaned_sender, "model", ai_response)

        # Envia a resposta de volta ao WhatsApp via Evolution API
        await send_text_message(cleaned_sender, ai_response)

        # Atualiza a reação para indicar conclusão
        if message_key:
            await send_reaction(message_key, "✅")

        # Controle Inteligente de Áudio (por padrão em texto só envia áudio se solicitado ou se /voz on)
        if should_send_audio(cleaned_sender, message_text, is_incoming_audio=False):
            try:
                await send_audio_message(cleaned_sender, ai_response)
            except Exception as audio_err:
                print(f"⚠️ [Audio Send Warning]: {audio_err}")

    except Exception as e:
        print(f"❌ [Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro no processamento: {e}")
        if message_key:
            await send_reaction(message_key, "❌")

async def process_whatsapp_audio(sender_number: str, payload_data: dict, mimetype: str, message_key: dict = None, is_group: bool = False):
    """
    Processa mensagem de áudio:
    1. Baixa o áudio via Evolution API
    2. Transcreve o áudio com Gemini Multimodal (<1s)
    3. Se for em grupo, verifica se contém gatilho explícito (@aura ou aura)
    4. Envia o texto resultante para o Roteador Inteligente (Fast-Path ~2s ou AGY)
    5. Responde em texto e voz (Francisca Neural) se modo de voz permitir (auto/on)
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    try:
        # 1. Baixa o conteúdo Base64 do áudio
        audio_base64 = await fetch_media_base64(payload_data)
        
        if not audio_base64:
            print(f"⚠️ [Audio Download Warning] Não foi possível baixar áudio de {cleaned_sender}")
            return

        # 2. Transcrição do áudio ultrarrápida (Gemini Flash async)
        transcription = await transcribe_audio(audio_base64, mimetype)
        if not transcription:
            print(f"⚠️ [Audio Empty] Transcrição vazia para áudio de {cleaned_sender}")
            return

        # Regra Estrita para Grupos: NUNCA responder se não foi chamada explicitamente por @aura ou aura
        if is_group:
            lower_trans = transcription.lower()
            has_trigger = "@aura" in lower_trans or "aura" in lower_trans
            if not has_trigger:
                print(f"🔇 [Áudio Ignorado em Grupo {cleaned_sender}]: Não continha menção à Aura. Texto: '{transcription[:60]}...'")
                return

        # Somente sinaliza presença e reação se for responder
        await send_presence(cleaned_sender, "recording")
        if message_key:
            await send_reaction(message_key, "🎙️")

        history = get_recent_history(cleaned_sender, limit=14)
        add_message(cleaned_sender, "user", f"[Áudio]: {transcription}")

        # 3. Execução no Roteador Inteligente
        print(f"📝 [Transcrição Áudio de {cleaned_sender}]: {transcription}")
        ai_response = await route_and_execute(cleaned_sender, transcription, history)

        add_message(cleaned_sender, "model", ai_response)

        # 4. Envia resposta em TEXTO IMEDIATAMENTE (sem esperar geração de áudio)
        await send_text_message(cleaned_sender, ai_response)

        if message_key:
            await send_reaction(message_key, "✅")

        # 5. Envia resposta em VOZ se modo de voz for 'auto' (padrão para áudio recebido) ou 'on'
        if should_send_audio(cleaned_sender, transcription or "", is_incoming_audio=True):
            try:
                await send_audio_message(cleaned_sender, ai_response)
            except Exception as audio_err:
                print(f"⚠️ [Audio Send Warning]: {audio_err}")

    except Exception as e:
        print(f"❌ [Audio Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro ao processar seu áudio: {e}")
        if message_key:
            await send_reaction(message_key, "❌")

async def process_whatsapp_media(
    sender_number: str,
    payload_data: dict,
    mimetype: str,
    caption: str = "",
    file_name: str = "",
    is_document: bool = False,
    message_key: dict = None
):
    """
    Processa imagens (comprovantes, recibos, prints, fotos) e documentos (PDF, CSV, TXT):
    1. Reage com 🖼️ ou 📄
    2. Baixa mídia em Base64 via Evolution API
    3. Analisa com Gemini 2.5 Flash Multimodal + Tools (podendo lançar gastos no Cofre)
    4. Envia resposta em texto e atualiza reação para ✅
    """
    cleaned_sender = "".join(filter(str.isdigit, sender_number))
    reaction_emoji = "📄" if is_document else "🖼️"
    try:
        await send_presence(cleaned_sender, "composing")
        if message_key:
            await send_reaction(message_key, reaction_emoji)

        media_base64 = await fetch_media_base64(payload_data)
        if not media_base64:
            await send_text_message(cleaned_sender, "⚠️ Recebi o arquivo/imagem, mas não foi possível baixar a mídia da Evolution API.")
            if message_key:
                await send_reaction(message_key, "❌")
            return

        history = get_recent_history(cleaned_sender, limit=10)
        label = f"[Documento: {file_name or mimetype}]" if is_document else f"[Imagem: {mimetype}]"
        add_message(cleaned_sender, "user", f"{label} {caption}".strip())

        ai_response = await asyncio.to_thread(
            generate_ai_response_from_media,
            cleaned_sender,
            media_base64,
            mimetype,
            caption,
            file_name,
            history
        )

        add_message(cleaned_sender, "model", ai_response)
        await send_text_message(cleaned_sender, ai_response)

        if message_key:
            await send_reaction(message_key, "✅")

        if should_send_audio(cleaned_sender, caption, is_incoming_audio=False):
            try:
                await send_audio_message(cleaned_sender, ai_response)
            except Exception as audio_err:
                print(f"⚠️ [Audio Send Warning]: {audio_err}")

    except Exception as e:
        print(f"❌ [Media Task Error]: {e}")
        await send_text_message(cleaned_sender, f"⚠️ Ocorreu um erro ao analisar a mídia: {e}")
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
        is_group = "@g.us" in remote_jid
        chat_target = remote_jid if is_group else "".join(filter(str.isdigit, remote_jid.split("@")[0]))
        
        participant = key.get("participant", "") or payload_data.get("participant", "")
        sender_digits = "".join(filter(str.isdigit, (participant or remote_jid).split("@")[0]))

        # Verifica se é grupo autorizado
        is_allowed_group = False
        if is_group:
            group_id = remote_jid.split("@")[0]
            is_allowed_group = any(g in remote_jid or group_id in g for g in settings.allowed_groups)

        # Se fromMe == True (ex: enviando mensagem para si mesmo no WhatsApp ou enviada pelo dono no grupo)
        if key.get("fromMe") is True:
            is_owner = any(owner in sender_digits or sender_digits in owner for owner in settings.owner_numbers)
            if not is_owner and not is_allowed_group:
                return JSONResponse({"status": "ignored", "reason": "message_from_me"})

        # Segurança: No privado exige ser dono; em grupo exige que o grupo esteja autorizado
        if is_group:
            if not is_allowed_group:
                print(f"⚠️ [Security] Mensagem recebida de grupo não autorizado: {remote_jid}")
                return JSONResponse({"status": "unauthorized", "reason": "group_not_allowed"})
        else:
            authorized = any(owner in sender_digits or sender_digits in owner for owner in settings.owner_numbers)
            if not authorized:
                print(f"⚠️ [Security] Mensagem recebida de número não autorizado: {sender_digits}")
                return JSONResponse({"status": "unauthorized", "reason": "number_not_in_owner_list"})

        message = payload_data.get("message", {})

        # Extrai o texto da mensagem (ou legenda) para verificar menção em grupo
        message_text = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text") or
            message.get("imageMessage", {}).get("caption") or
            message.get("documentMessage", {}).get("caption") or
            message.get("documentWithCaptionMessage", {}).get("message", {}).get("documentMessage", {}).get("caption") or
            ""
        )

        # Verifica se é mensagem de áudio (audioMessage)
        audio_msg = message.get("audioMessage")
        if audio_msg:
            raw_mime = audio_msg.get("mimetype", "audio/ogg")
            mimetype = raw_mime.split(";")[0]
            print(f"🎙️ [Áudio Recebido de {chat_target}]: formato {mimetype}")
            task = BackgroundTask(process_whatsapp_audio, chat_target, payload_data, mimetype, key, is_group)
            return JSONResponse({"status": "processing_audio", "sender": chat_target}, background=task)

        # Regra de Grupo para mensagens de texto/mídia: Só responde se contiver @aura ou aura
        if is_group:
            has_trigger = "@aura" in message_text.lower() or message_text.lower().startswith("aura")
            if not has_trigger:
                return JSONResponse({"status": "ignored", "reason": "group_message_without_aura_mention"})

        # Verifica se é mensagem de imagem (imageMessage)
        image_msg = message.get("imageMessage")
        if image_msg:
            mimetype = image_msg.get("mimetype", "image/jpeg").split(";")[0]
            caption = image_msg.get("caption", "")
            print(f"🖼️ [Imagem Recebida de {chat_target}]: {mimetype} | Legenda: {caption}")
            task = BackgroundTask(
                process_whatsapp_media, chat_target, payload_data, mimetype, caption, "", False, key
            )
            return JSONResponse({"status": "processing_image", "sender": chat_target}, background=task)

        # Verifica se é documento (documentMessage ou documentWithCaptionMessage)
        doc_msg = (
            message.get("documentMessage") or
            message.get("documentWithCaptionMessage", {}).get("message", {}).get("documentMessage")
        )
        if doc_msg:
            mimetype = doc_msg.get("mimetype", "application/pdf").split(";")[0]
            caption = doc_msg.get("caption", "")
            file_name = doc_msg.get("fileName", "documento")
            print(f"📄 [Documento Recebido de {chat_target}]: {file_name} ({mimetype})")
            task = BackgroundTask(
                process_whatsapp_media, chat_target, payload_data, mimetype, caption, file_name, True, key
            )
            return JSONResponse({"status": "processing_document", "sender": chat_target}, background=task)

        if not message_text:
            return JSONResponse({"status": "ignored", "reason": "no_supported_content"})

        print(f"📩 [Mensagem Recebida de {chat_target} (de: {sender_digits})]: {message_text}")

        # Processa texto em background com identificador real do emissor para RBAC
        task = BackgroundTask(process_whatsapp_message, chat_target, message_text, key, sender_digits)
        return JSONResponse({"status": "processing", "sender": chat_target}, background=task)

    # Eventos de conexão da Evolution API
    if event in ["connection.update", "status.instance"]:
        payload_data = data.get("data", {})
        state = payload_data.get("state") or payload_data.get("status")
        print(f"📡 [Evolution Event] {event}: state={state}")
        return JSONResponse({"status": "acknowledged", "state": state})

    return JSONResponse({"status": "ignored", "event": event})
