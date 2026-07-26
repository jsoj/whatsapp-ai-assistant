from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert json_data["app"] == "whatsapp-ai-assistant"
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
                "remoteJid": "554388597348@s.whatsapp.net",
                "fromMe": True
            },
            "message": {
                "conversation": "Mensagem enviada por mim"
            }
        }
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

def test_webhook_authorized_owner():
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
