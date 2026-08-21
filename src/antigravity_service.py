import os
import asyncio
import base64
import time
from pathlib import Path
from google import genai
from google.genai import types

from src.config import settings
from src.memory import get_agy_session, set_agy_session, reset_agy_session
from src.gemini_service import generate_ai_response

def get_brain_sessions() -> set[str]:
    """Retorna o conjunto de IDs de conversas existentes no diretório brain do Antigravity."""
    brain_dir = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if not brain_dir.exists():
        return set()
    return {d.name for d in brain_dir.iterdir() if d.is_dir() and len(d.name) == 36}

def clean_agy_output(raw_output: str) -> str:
    """Limpa avisos do CLI e formata a resposta para o WhatsApp."""
    lines = raw_output.splitlines()
    clean_lines = []
    for line in lines:
        if line.strip().startswith("warning: conversation") or line.strip().startswith("warn:"):
            continue
        clean_lines.append(line)
    
    result = "\n".join(clean_lines).strip()
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

    # 3. Monta comando
    cmd = [agy_bin, "-p", prompt, "--dangerously-skip-permissions"]
    if existing_session:
        cmd.extend(["--conversation", existing_session])

    print(f"🤖 [Antigravity Service] Executando agy para {phone_number} (Sessão: {existing_session or 'Nova'})...")
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
            # Fallback para o Gemini direto caso agy retorne vazio ou erro
            return generate_ai_response(phone_number, prompt, [])

    except Exception as e:
        print(f"❌ [Antigravity Service Error]: {e}. Acionando fallback Gemini...")
        return generate_ai_response(phone_number, prompt, [])

def transcribe_audio(audio_base64: str, mime_type: str = "audio/ogg") -> str | None:
    """
    Transcreve áudio com o Gemini Multimodal para encaminhar como texto ao Antigravity.
    """
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

    for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.6-flash"]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[audio_part, prompt]
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"⚠️ [Audio Transcription Error] Modelo {model_name}: {e}")
            continue

    return None
