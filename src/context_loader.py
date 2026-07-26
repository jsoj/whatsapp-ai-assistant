import os
from pathlib import Path
from src.config import settings

def load_agents_context() -> str:
    """
    Carrega dinamicamente o arquivo AGENTS.md e o contexto de ambiente/projetos.
    """
    possible_paths = [
        Path(settings.CONTEXT_FILE_PATH),
        Path.home() / ".gemini" / "config" / "AGENTS.md",
        Path.home() / "dev" / "context" / "AGENTS.md",
    ]

    context_content = ""
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    context_content = f.read()
                    break
            except Exception as e:
                print(f"[ContextLoader Warning] Não foi possível ler {path}: {e}")

    system_persona = (
        "Você é o Antigravity, o assistente pessoal de IA e copiloto de desenvolvimento do Junior via WhatsApp.\n"
        "Você responde diretamente nas conversas do WhatsApp com o Junior ou administradores do ambiente.\n\n"
        "--- DIRETRIZES DE COMUNICAÇÃO NO WHATSAPP ---\n"
        "1. Seja direto, conciso, profissional e extremamente prestativo.\n"
        "2. Use formatação nativa do WhatsApp quando útil (*negrito*, _itálico_, `código monospaçado`).\n"
        "3. Você possui pleno conhecimento sobre a infraestrutura da VPS (Hostinger Coolify http://72.61.135.23), "
        "projetos da Fersie (roupas/bijoux - Sibele), IAG (análise de solo/genética - Matheus/Junior), "
        "regras de isolamento LGPD e repositórios Git.\n"
        "4. Mantenha o contexto e responda considerando a conversa anterior do usuário.\n\n"
        "--- CONTEXTO E REGRAS GLOBAIS DO AMBIENTE ---\n"
    )

    if context_content:
        return system_persona + context_content
    else:
        return system_persona + "\n(Contexto global AGENTS.md não foi localizado no disco local)."
