from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.antigravity_service import handle_instant_command, should_send_audio

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["app"] == "whatsapp-ai-assistant"
    assert json_data["version"] == "2.5.0"
    assert "554388597348" in json_data["authorized_owners"]

def test_webhook_unauthorized_number():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "conversation": "Tentativa de acesso não autorizado"
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "unauthorized"

def test_webhook_ignored_from_me():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "5511888888888@s.whatsapp.net",
                "fromMe": True
            },
            "message": {
                "conversation": "Mensagem enviada por mim não autorizada"
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

@patch("src.main.process_whatsapp_message", new_callable=AsyncMock)
def test_webhook_authorized_owner(mock_process_msg):
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "554388597348@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "conversation": "Qual é a lista de domínios configurados?"
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    mock_process_msg.assert_awaited_once()

@patch("src.main.process_whatsapp_audio", new_callable=AsyncMock)
def test_webhook_audio_message(mock_process_audio):
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "554388597348@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "audioMessage": {
                    "mimetype": "audio/ogg; codecs=opus"
                }
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processing_audio"
    mock_process_audio.assert_awaited_once()

@patch("src.main.process_whatsapp_media", new_callable=AsyncMock)
def test_webhook_image_message(mock_process_media):
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "554388597348@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "imageMessage": {
                    "mimetype": "image/jpeg",
                    "caption": "Comprovante almoço"
                }
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processing_image"
    mock_process_media.assert_awaited_once()

@patch("src.main.process_whatsapp_media", new_callable=AsyncMock)
def test_webhook_document_message(mock_process_media):
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "554388597348@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "documentMessage": {
                    "mimetype": "application/pdf",
                    "fileName": "fatura.pdf",
                    "caption": "Analise esta fatura"
                }
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "processing_document"
    mock_process_media.assert_awaited_once()

def test_instant_commands_and_smart_audio():
    test_phone = "5543999999999"
    # /ajuda
    help_res = handle_instant_command(test_phone, "/ajuda")
    assert help_res is not None
    assert "Central de Comandos" in help_res

    # /voz auto (default), /voz on, /voz off
    res_auto = handle_instant_command(test_phone, "/voz auto")
    assert "AUTO" in res_auto
    assert should_send_audio(test_phone, "Oi tudo bem?", is_incoming_audio=False) is False
    assert should_send_audio(test_phone, "Me responda em áudio por favor", is_incoming_audio=False) is True
    assert should_send_audio(test_phone, "Qualquer texto", is_incoming_audio=True) is True

    res_on = handle_instant_command(test_phone, "/voz on")
    assert "SEMPRE ATIVO" in res_on
    assert should_send_audio(test_phone, "Oi tudo bem?", is_incoming_audio=False) is True

    res_off = handle_instant_command(test_phone, "/voz off")
    assert "DESATIVADO" in res_off
    assert should_send_audio(test_phone, "Me responda em áudio", is_incoming_audio=True) is False

    # Restaura auto e modo fast
    handle_instant_command(test_phone, "/voz auto")
    mode_res = handle_instant_command(test_phone, "/modo fast")
    assert "FAST-PATH" in mode_res

    # /foco
    foco_res = handle_instant_command(test_phone, "/foco")
    assert foco_res is not None
    assert "TRILHO" in foco_res or "MISSÃO" in foco_res

