import os
import re
import asyncio
import base64
import time
from pathlib import Path
from google import genai
from google.genai import types

from src.config import settings
from src.memory import (
    get_agy_session,
    set_agy_session,
    reset_agy_session,
    clear_history,
    get_user_prefs,
    set_user_prefs,
)
from src.gemini_service import generate_ai_response
from src.tools import (
    get_system_status,
    estacionar_ideia_trilho,
    registrar_gasto_pessoal,
    consultar_cofre_notas,
)

HELP_MESSAGE = (
    "🤖 *Central de Comandos — WhatsApp AI Assistant 2.5*\n\n"
    "⚡ *Atalhos Instantâneos (<0.2s):*\n"
    "• `/status` — Saúde da VPS, RAM, Disco, Docker e Modo ativo\n"
    "• `/foco` ou `/trilho` — Exibe a Missão Única Ativa e o Estacionamento\n"
    "• `Estacione: [ideia]` — Grava ideia no Trilho sem perder o foco\n"
    "• `/gasto [valor] [categoria] [descrição]` — Lança despesa em `Gastos_Pessoais.md`\n"
    "• `/cofre [termo]` — Busca ou lê notas no Cofre (`index`, `iag`, `gastos`, `saude`, `tarefas`)\n"
    "• `/emails [agromarkers|pessoal|icloud]` — Lista e-mails recentes da AURA\n"
    "• `/novo` ou `/reset` — Reinicia sessão e limpa memória recente\n\n"
    "🎛️ *Controle de Voz e Motor:*\n"
    "• `/voz auto` — Áudio só quando você envia áudio ou pede (Padrão)\n"
    "• `/voz on` — Responde sempre em texto + áudio\n"
    "• `/voz off` — Responde apenas em texto\n"
    "• `/modo fast` — Rota Rápida Gemini 2.5 Flash (~2s) + Tools (Padrão)\n"
    "• `/modo agy` — Força sempre o motor profundo `agy` CLI (~25s)\n"
    "• `/agy [instrução]` — Executa um comando pontual no `agy` CLI completo\n\n"
    "🖼️ *Multimodal:* Envie áudios, fotos de comprovantes/recibos ou PDFs!"
)

DEEP_AGENT_KEYWORDS = (
    "use o agy",
    "usar o agy",
    "antigravity cli",
    "refatore",
    "subagente",
    "stitch",
)

def should_send_audio(phone_number: str, user_text: str = "", is_incoming_audio: bool = False) -> bool:
    """Decide de forma inteligente se deve enviar resposta sintetizada por voz (Edge-TTS)."""
    prefs = get_user_prefs(phone_number)
    mode = prefs.get("voice_mode", "auto")
    if mode == "off":
        return False
    if mode == "on":
        return True
    # Modo 'auto': responde com áudio quando recebe áudio ou quando solicitado no texto
    if is_incoming_audio:
        return True
    lower_text = (user_text or "").lower()
    audio_triggers = ("em áudio", "em audio", "manda áudio", "manda audio", "responda em áudio", "responda por voz", "fale em áudio")
    return any(t in lower_text for t in audio_triggers)

def handle_instant_command(phone_number: str, prompt: str) -> str | None:
    """
    Executa atalhos determinísticos em <0.1s sem custo de LLM.
    Retorna a resposta pronta ou None se não for um comando instantâneo.
    """
    clean = prompt.strip()
    lower = clean.lower()

    # 1. Menu de Ajuda
    if lower in ("/ajuda", "/help", "/menu", "/comandos"):
        prefs = get_user_prefs(phone_number)
        return (
            f"{HELP_MESSAGE}\n\n"
            f"📌 *Configuração Atual:* Motor `{prefs['engine_mode']}` | Voz `{prefs['voice_mode']}`"
        )

    # 2. Reset de Sessão e Memória
    if lower in ("/reset", "/novo", "/reiniciar", "reset", "novo contexto"):
        clear_history(phone_number)
        return "🔄 *Sessão e memória recente reiniciadas com sucesso!* Uma nova linha de raciocínio limpa foi iniciada."

    # 3. Status da VPS
    if lower in ("/status", "status vps"):
        prefs = get_user_prefs(phone_number)
        session = get_agy_session(phone_number) or "Nenhuma"
        sys_report = get_system_status()
        return (
            f"{sys_report}\n\n"
            f"⚙️ *Assistente WhatsApp:*\n"
            f"• Motor Padrão: `{prefs['engine_mode'].upper()}`\n"
            f"• Modo de Voz: `{prefs['voice_mode'].upper()}`\n"
            f"• Sessão AGY: `{session}`"
        )

    # 4. Consulta rápida ao Trilho de Foco
    if lower in ("/foco", "/trilho"):
        return consultar_cofre_notas("foco")

    # 5. Estacionamento imediato de digressões ("Estacione: ..." ou "/estacionar ...")
    if lower.startswith("estacione:") or lower.startswith("/estacionar ") or lower.startswith("/estacione "):
        idea = re.sub(r"^(estacione:|/estacionar|/estacione)\s*", "", clean, flags=re.IGNORECASE).strip()
        if not idea:
            return "⚠️ Informe a ideia após o comando. Exemplo: `Estacione: Revisar contrato com laboratório`"
        return estacionar_ideia_trilho(idea)

    # 6. Registro rápido de gasto ("/gasto 85.50 Refeição Almoço cliente")
    if lower.startswith("/gasto"):
        parts = clean.split(maxsplit=3)
        if len(parts) < 3:
            return "⚠️ Formato: `/gasto [valor] [categoria] [descrição]`\nExemplo: `/gasto 65.00 Refeição Almoço no PIX`"
        try:
            val_str = parts[1].replace("R$", "").replace(",", ".").strip()
            valor = float(val_str)
            categoria = parts[2]
            descricao = parts[3] if len(parts) > 3 else categoria
            return registrar_gasto_pessoal(valor=valor, categoria=categoria, descricao=descricao)
        except ValueError:
            return "⚠️ Valor numérico inválido. Exemplo: `/gasto 65.00 Refeição Almoço`"

    # 7. Consulta rápida ao Cofre ("/cofre [termo]")
    if lower == "/cofre" or lower.startswith("/cofre "):
        arg = clean[6:].strip() or "index"
        return consultar_cofre_notas(arg)

    # 8. Controle de Voz ("/voz [auto|on|off]")
    if lower == "/voz" or lower.startswith("/voz "):
        arg = clean[4:].strip().lower()
        mapping = {
            "auto": "auto",
            "automatico": "auto",
            "automático": "auto",
            "on": "on",
            "sempre": "on",
            "ativo": "on",
            "off": "off",
            "nunca": "off",
            "mudo": "off",
            "texto": "off",
        }
        if arg in mapping:
            updated = set_user_prefs(phone_number, voice_mode=mapping[arg])
            labels = {
                "auto": "🎙️ *Modo de Voz: AUTO* (Responde em áudio apenas quando você envia áudio ou pede explicitamente).",
                "on": "🔊 *Modo de Voz: SEMPRE ATIVO* (Todas as respostas incluirão áudio da Francisca Neural).",
                "off": "🔇 *Modo de Voz: DESATIVADO* (Respostas apenas em texto).",
            }
            return labels[updated["voice_mode"]]
        prefs = get_user_prefs(phone_number)
        return (
            f"🎙️ *Modo de Voz atual:* `{prefs['voice_mode']}`\n"
            "Use `/voz auto`, `/voz on` ou `/voz off` para alterar."
        )

    # 9. Controle de Motor ("/modo [fast|agy]")
    if lower == "/modo" or lower.startswith("/modo "):
        arg = clean[5:].strip().lower()
        if arg in ("fast", "rapido", "rápido", "flash"):
            set_user_prefs(phone_number, engine_mode="fast")
            return "⚡ *Motor alterado para: FAST-PATH (Gemini 2.5 Flash + Tools)* — Respostas em ~2 segundos!"
        if arg in ("agy", "deep", "profundo", "completo"):
            set_user_prefs(phone_number, engine_mode="agy")
            return "🤖 *Motor alterado para: AGY CLI COMPLETO* — Todas as mensagens usarão o subprocesso `agy`."
        prefs = get_user_prefs(phone_number)
        return (
            f"⚙️ *Motor atual:* `{prefs['engine_mode']}`\n"
            "Use `/modo fast` (~2s) ou `/modo agy` (~25s)."
        )

    # 10. Consulta rápida a e-mails ("/emails [agromarkers|pessoal]" ou "/email")
    if lower == "/emails" or lower == "/email" or lower.startswith("/emails ") or lower.startswith("/email "):
        from src.tools import consultar_emails_aura
        arg = clean.split(maxsplit=1)[1].lower() if " " in clean else "agromarkers"
        account_map = {
            "agromarkers": "gmail_agromarkers",
            "agro": "gmail_agromarkers",
            "iag": "gmail_agromarkers",
            "pessoal": "gmail_pessoal",
            "junior": "gmail_pessoal",
            "icloud": "icloud_pessoal",
            "apple": "icloud_pessoal",
            "me": "icloud_pessoal",
        }
        target_acc = account_map.get(arg, "gmail_agromarkers")
        return consultar_emails_aura(conta=target_acc, limite=4)

    return None

async def route_and_execute(
    phone_number: str,
    prompt: str,
    history: list[dict] = None,
    custom_system_instruction: str = None,
    sender_digits: str = None
) -> str:
    """
    Roteador Inteligente Híbrido:
    1. Comandos Instantâneos (<0.1s)
    2. Fast-Path (Gemini 2.5 Flash + Tools + Contexto em ~2s) com RBAC de ferramentas
    3. Deep-Path (Subprocesso Antigravity CLI `agy` quando solicitado ou modo=agy)
    """
    clean = prompt.strip()

    # 1. Rota Instantânea (<0.1s)
    instant_reply = handle_instant_command(phone_number, clean)
    if instant_reply is not None:
        print(f"⚡ [Instant Command] Respondido imediatamente para {phone_number}")
        return instant_reply

    # 2. Forçar execução no AGY via prefixo (/agy, /agente, /deep)
    lower = clean.lower()
    if lower.startswith("/agy ") or lower.startswith("/agente ") or lower.startswith("/deep "):
        sub_prompt = clean.split(maxsplit=1)[1] if " " in clean else clean
        return await run_antigravity_agent(phone_number, sub_prompt)

    # 3. Verifica preferência de motor do usuário ou palavras-chave de engenharia profunda
    prefs = get_user_prefs(phone_number)
    needs_deep_agent = prefs.get("engine_mode") == "agy" or any(k in lower for k in DEEP_AGENT_KEYWORDS)

    if needs_deep_agent and settings.USE_ANTIGRAVITY_AGENT:
        return await run_antigravity_agent(phone_number, clean)

    # 4. Rota Rápida Padrão (Fast-Path: Gemini 2.5 Flash + Tools + Memória em ~1.5-2.5s)
    start_t = time.time()
    print(f"🚀 [Fast-Path] Processando mensagem para {phone_number} (sender: {sender_digits}) via Gemini 2.5 Flash + Tools...")
    response = await asyncio.to_thread(
        generate_ai_response,
        phone_number,
        clean,
        history or [],
        custom_system_instruction,
        sender_digits
    )
    print(f"⚡ [Fast-Path Finished] Concluído em {time.time() - start_t:.2f}s")
    return response


def get_brain_sessions() -> set[str]:
    """Retorna o conjunto de IDs de conversas existentes no diretório brain do Antigravity."""
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists():
        return set()
    return {d.name for d in brain_dir.iterdir() if d.is_dir() and len(d.name) == 36}

def clean_agy_output(raw_output: str) -> str:
    """Limpa avisos do CLI e converte eventuais tabelas/títulos markdown para padrão estrito WhatsApp."""
    lines = raw_output.splitlines()
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("warning: conversation") or stripped.startswith("warn:"):
            continue
            
        # Converte títulos markdown (#, ##, ###) em negrito com quebra limpa
        if re.match(r"^#{1,6}\s+", stripped):
            clean_title = re.sub(r"^#{1,6}\s+", "", stripped)
            clean_lines.append(f"\n*{clean_title}*")
            continue
            
        # Ignora separadores de tabela (|---|---|)
        if re.match(r"^\|?(\s*:?-+:?\s*\|)+\s*$", stripped):
            continue
            
        # Converte linhas de tabela (| A | B | C |) em tópicos com marcadores
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            valid_cells = [c for c in cells if c and not re.match(r"^:?-+:?$", c)]
            if valid_cells:
                clean_lines.append("• " + " — ".join(valid_cells))
            continue

        # Remove links markdown [texto](url) mantendo apenas o texto ou URL limpa
        stripped_links = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
        clean_lines.append(stripped_links)
    
    result = "\n".join(clean_lines).strip()
    # Remove excesso de quebras consecutivas
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result or "Ação processada com sucesso pelo Antigravity."
    return result or "Ação processada com sucesso pelo Antigravity."

async def run_antigravity_agent(phone_number: str, prompt: str) -> str:
    """
    Executa a instrução do WhatsApp diretamente no motor do Antigravity (agy).
    Mantém o histórico contínuo de sessão e tem acesso a todas as ferramentas e contexto.
    """
    # 1. Comandos de reset de sessão
    clean_prompt = prompt.strip()
    if clean_prompt.lower() in ["/reset", "/novo", "/reiniciar", "reset", "novo contexto"]:
        reset_agy_session(phone_number)
        return "🔄 *Sessão reiniciada com sucesso!* Uma nova linha de raciocínio limpa será iniciada na próxima mensagem."

    agy_bin = settings.AGY_BIN_PATH
    if not os.path.exists(agy_bin):
        import shutil
        agy_bin = shutil.which("agy") or "/root/.local/bin/agy"

    # 2. Obtém sessão existente (se válida)
    existing_session = get_agy_session(phone_number)
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if existing_session and not (brain_dir / existing_session).exists():
        existing_session = None

    # Mapeia sessões anteriores para detectar nova criação
    before_sessions = get_brain_sessions()

    # 3. Monta comando otimizado para velocidade
    cmd = [
        agy_bin,
        "-p", prompt,
        "--effort", settings.AGY_EFFORT,
        "--disable-slash-commands",
        "--dangerously-skip-permissions"
    ]
    if existing_session:
        cmd.extend(["--conversation", existing_session])

    print(f"🤖 [Antigravity Service] Executando agy para {phone_number} (Sessão: {existing_session or 'Nova'}, Effort: {settings.AGY_EFFORT})...")
    start_time = time.time()

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=settings.AGY_WORKSPACE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(settings.AGY_TIMEOUT))
        except asyncio.TimeoutError:
            proc.kill()
            print(f"⏱️ [Antigravity Timeout] Timeout de {settings.AGY_TIMEOUT}s atingido. Acionando fallback Gemini...")
            return generate_ai_response(phone_number, prompt, [])

        elapsed = time.time() - start_time
        out_text = stdout.decode("utf-8", errors="replace").strip()
        err_text = stderr.decode("utf-8", errors="replace").strip()

        print(f"⚡ [Antigravity Finished] Concluído em {elapsed:.1f}s com código {proc.returncode}")

        if proc.returncode == 0 and out_text:
            # 4. Salva a nova sessão detectada se não existia
            if not existing_session:
                after_sessions = get_brain_sessions()
                new_created = after_sessions - before_sessions
                if new_created:
                    new_session_id = next(iter(new_created))
                    set_agy_session(phone_number, new_session_id)
                    print(f"💾 [Antigravity Session] Nova sessão vinculada a {phone_number}: {new_session_id}")

            return clean_agy_output(out_text)
        else:
            print(f"⚠️ [Antigravity Non-Zero/Empty] Return code: {proc.returncode}. Stderr: {err_text[:300]}")
            return generate_ai_response(phone_number, prompt, [])

    except Exception as e:
        print(f"❌ [Antigravity Service Error]: {e}. Acionando fallback Gemini...")
        return generate_ai_response(phone_number, prompt, [])

def _sync_transcribe(audio_base64: str, mime_type: str) -> str | None:
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)
    raw_bytes = base64.b64decode(audio_base64)
    audio_part = types.Part.from_bytes(
        data=raw_bytes,
        mime_type=mime_type or "audio/ogg"
    )

    prompt = "Transcreva com máxima fidelidade e em português brasileiro exatamente o que foi falado neste áudio. Retorne APENAS a transcrição pura, sem aspas, explicações ou notas."

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[audio_part, prompt],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            )
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"⚠️ [Audio Transcription Error]: {e}")
    return None

async def transcribe_audio(audio_base64: str, mime_type: str = "audio/ogg") -> str | None:
    """
    Transcreve áudio com o Gemini Multimodal de forma assíncrona (1-2s).
    """
    return await asyncio.to_thread(_sync_transcribe, audio_base64, mime_type)
