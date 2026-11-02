import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega arquivo .env se existir
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    @property
    def EVOLUTION_URL(self) -> str:
        return os.getenv("EVOLUTION_URL", "https://evolution.quantisia.com.br").rstrip("/")

    @property
    def EVOLUTION_APIKEY(self) -> str:
        return os.getenv("EVOLUTION_APIKEY", "")

    @property
    def EVOLUTION_INSTANCE(self) -> str:
        return os.getenv("EVOLUTION_INSTANCE", "01")

    @property
    def GEMINI_API_KEY(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def GEMINI_MODEL(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @property
    def OWNER_NUMBERS_RAW(self) -> str:
        return os.getenv("OWNER_NUMBERS", "554388597348,5543988597348")

    @property
    def ALLOWED_GROUPS_RAW(self) -> str:
        return os.getenv(
            "ALLOWED_GROUPS",
            "120363147621109705@g.us,120363064087395658@g.us,120363423519539092@g.us"
        )

    @property
    def DB_PATH(self) -> str:
        return os.getenv("DB_PATH", "data/conversations.db")

    @property
    def CONTEXT_FILE_PATH(self) -> str:
        return os.getenv("CONTEXT_FILE_PATH", str(Path.home() / ".gemini" / "config" / "AGENTS.md"))

    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", "8000"))

    @property
    def AGY_BIN_PATH(self) -> str:
        return os.getenv("AGY_BIN_PATH", "/root/.local/bin/agy")

    @property
    def AGY_WORKSPACE(self) -> str:
        return os.getenv("AGY_WORKSPACE", "/root")

    @property
    def AGY_TIMEOUT(self) -> int:
        return int(os.getenv("AGY_TIMEOUT", "180"))

    @property
    def AGY_EFFORT(self) -> str:
        return os.getenv("AGY_EFFORT", "low")

    @property
    def USE_ANTIGRAVITY_AGENT(self) -> bool:
        return os.getenv("USE_ANTIGRAVITY_AGENT", "true").lower() in ("true", "1", "yes")

    @property
    def owner_numbers(self) -> list[str]:
        """Retorna a lista de números autorizados higienizados (apenas dígitos)."""
        numbers = []
        for num in self.OWNER_NUMBERS_RAW.split(","):
            cleaned = "".join(filter(str.isdigit, num.strip()))
            if cleaned:
                numbers.append(cleaned)
        return numbers

    @property
    def allowed_groups(self) -> list[str]:
        """Retorna a lista de IDs de grupos autorizados (ex: 120363147621109705@g.us ou apenas dígitos)."""
        groups = []
        for g in self.ALLOWED_GROUPS_RAW.split(","):
            cleaned = g.strip()
            if cleaned:
                groups.append(cleaned)
                digits = "".join(filter(str.isdigit, cleaned.split("@")[0]))
                if digits and digits not in groups:
                    groups.append(digits)
        return groups

settings = Settings()
