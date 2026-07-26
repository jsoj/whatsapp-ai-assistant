import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega arquivo .env se existir
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    EVOLUTION_URL: str = os.getenv("EVOLUTION_URL", "https://evolution.projetobrasil2050.site").rstrip("/")
    EVOLUTION_APIKEY: str = os.getenv("EVOLUTION_APIKEY", "6CBB7DCE6D50-4851-A607-F2EC2C1580C2")
    EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "01")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Números autorizados (separados por vírgula)
    OWNER_NUMBERS_RAW: str = os.getenv("OWNER_NUMBERS", "554388597348")

    DB_PATH: str = os.getenv("DB_PATH", "data/conversations.db")
    CONTEXT_FILE_PATH: str = os.getenv("CONTEXT_FILE_PATH", str(Path.home() / ".gemini" / "config" / "AGENTS.md"))
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def owner_numbers(self) -> list[str]:
        """Retorna a lista de números autorizados higienizados (apenas dígitos)."""
        numbers = []
        for num in self.OWNER_NUMBERS_RAW.split(","):
            cleaned = "".join(filter(str.isdigit, num.strip()))
            if cleaned:
                numbers.append(cleaned)
        return numbers

settings = Settings()
