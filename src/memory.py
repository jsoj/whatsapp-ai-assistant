import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone
from src.config import settings

def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = settings.DB_PATH

    path_obj = Path(db_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path_obj), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(db_path: str = None):
    """Inicializa as tabelas de conversas e sessões do Antigravity se não existirem."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_number TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_phone_timestamp ON messages (phone_number, timestamp)
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agy_sessions (
            phone_number TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            phone_number TEXT PRIMARY KEY,
            voice_mode TEXT NOT NULL DEFAULT 'auto',
            engine_mode TEXT NOT NULL DEFAULT 'fast',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_message(phone_number: str, role: str, content: str, db_path: str = None):
    """Adiciona uma mensagem ao histórico do usuário."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (phone_number, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (cleaned_number, role, content, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()

def get_recent_history(phone_number: str, limit: int = 14, db_path: str = None) -> list[dict]:
    """Retorna as mensagens recentes organizadas cronologicamente."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT role, content FROM (
            SELECT role, content, id FROM messages
            WHERE phone_number = ?
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id ASC
        """,
        (cleaned_number, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"]} for row in rows]

def clear_history(phone_number: str, db_path: str = None):
    """Limpa o histórico de conversa do número especificado."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE phone_number = ?", (cleaned_number,))
    cursor.execute("DELETE FROM agy_sessions WHERE phone_number = ?", (cleaned_number,))
    conn.commit()
    conn.close()

def get_agy_session(phone_number: str, db_path: str = None) -> str | None:
    """Busca o conversation_id do Antigravity para este número de telefone."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT conversation_id FROM agy_sessions WHERE phone_number = ?", (cleaned_number,))
    row = cursor.fetchone()
    conn.close()
    return row["conversation_id"] if row else None

def set_agy_session(phone_number: str, conversation_id: str, db_path: str = None):
    """Registra ou atualiza o conversation_id do Antigravity para este número."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO agy_sessions (phone_number, conversation_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(phone_number) DO UPDATE SET
            conversation_id = excluded.conversation_id,
            updated_at = excluded.updated_at
        """,
        (cleaned_number, conversation_id, now, now)
    )
    conn.commit()
    conn.close()

def reset_agy_session(phone_number: str, db_path: str = None):
    """Reseta a sessão do Antigravity forçando uma nova conversa na próxima mensagem."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agy_sessions WHERE phone_number = ?", (cleaned_number,))
    conn.commit()
    conn.close()

def get_user_prefs(phone_number: str, db_path: str = None) -> dict:
    """Retorna preferências do usuário (voice_mode: 'auto'|'on'|'off', engine_mode: 'fast'|'agy')."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT voice_mode, engine_mode FROM user_preferences WHERE phone_number = ?",
        (cleaned_number,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"voice_mode": row["voice_mode"], "engine_mode": row["engine_mode"]}
    return {"voice_mode": "auto", "engine_mode": "fast"}

def set_user_prefs(phone_number: str, voice_mode: str = None, engine_mode: str = None, db_path: str = None) -> dict:
    """Atualiza as preferências de voz ou motor para o usuário."""
    cleaned_number = "".join(filter(str.isdigit, phone_number))
    current = get_user_prefs(cleaned_number, db_path)
    new_voice = voice_mode if voice_mode in ("auto", "on", "off") else current["voice_mode"]
    new_engine = engine_mode if engine_mode in ("fast", "agy") else current["engine_mode"]
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_preferences (phone_number, voice_mode, engine_mode, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(phone_number) DO UPDATE SET
            voice_mode = excluded.voice_mode,
            engine_mode = excluded.engine_mode,
            updated_at = excluded.updated_at
        """,
        (cleaned_number, new_voice, new_engine, now)
    )
    conn.commit()
    conn.close()
    return {"voice_mode": new_voice, "engine_mode": new_engine}


