import os
import pytest
from pathlib import Path
from src.memory import init_db, add_message, get_recent_history, clear_history

TEST_DB = "data/test_conversations.db"

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_add_and_get_history():
    phone = "554388597348"
    add_message(phone, "user", "Olá, qual o status da VPS?", db_path=TEST_DB)
    add_message(phone, "model", "A VPS está rodando o Coolify em http://72.61.135.23", db_path=TEST_DB)

    history = get_recent_history(phone, limit=10, db_path=TEST_DB)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert "status da VPS" in history[0]["content"]
    assert history[1]["role"] == "model"
    assert "72.61.135.23" in history[1]["content"]

def test_clear_history():
    phone = "554388597348"
    add_message(phone, "user", "Mensagem teste", db_path=TEST_DB)
    clear_history(phone, db_path=TEST_DB)
    history = get_recent_history(phone, limit=10, db_path=TEST_DB)
    assert len(history) == 0
