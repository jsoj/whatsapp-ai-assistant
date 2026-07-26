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

    conn = sqlite3.connect(str(path_obj))
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = None):
    """Inicializa a tabela de conversas se não existir."""
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
    conn.commit()
    conn.close()
