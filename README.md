# 🤖 WhatsApp AI Assistant (Evolution API + Gemini)

Microserviço em **Python (FastAPI)** que conecta o seu WhatsApp (via **Evolution API**) ao modelo **Google Gemini (Gemini 2.5 Flash)** com conhecimento total sobre o seu ambiente de desenvolvimento, servidores (Coolify), regras de LGPD e projetos (Fersie & IAG).

---

## 📌 Funcionalidades

- 🧠 **Contexto Inteligente:** Carrega dinamicamente as diretrizes globais do projeto (`AGENTS.md`) e informações da VPS.
- 💾 **Memória de Conversa (SQLite):** Mantém o histórico cronológico de mensagens por número de telefone.
- 🔒 **Segurança & Controle de Acesso:** Responde apenas a números autorizados configurados em `OWNER_NUMBERS`.
- ⚡ **Alta Performance:** Processamento em segundo plano (FastAPI BackgroundTasks) para responder ao Webhook da Evolution API sem timeouts.
- 🐳 **Pronto para Coolify & Docker:** Inclui `Dockerfile` e `docker-compose.yml`.

---

## 🛠️ Variáveis de Ambiente (`.env`)

```env
EVOLUTION_URL=https://evolution.projetobrasil2050.site
EVOLUTION_APIKEY=6CBB7DCE6D50-4851-A607-F2EC2C1580C2
EVOLUTION_INSTANCE=01
GEMINI_API_KEY=sua_chave_gemini_aqui
GEMINI_MODEL=gemini-2.5-flash
OWNER_NUMBERS=554388597348
DB_PATH=data/conversations.db
PORT=8000
```

---

## 🧪 Rodando os Testes Automatizados

```bash
./venv/bin/pytest -v
```

---

## 🚀 Executando Localmente

```bash
# Ativar venv e rodar o servidor FastAPI
./venv/bin/uvicorn src.main:app --reload --port 8000
```

---

## 📡 Configurando o Webhook na Evolution API

Acesse a Evolution API ou execute a chamada HTTP para ativar o Webhook da sua instância:

```bash
curl -X POST "https://evolution.projetobrasil2050.site/webhook/set/01" \
  -H "apikey: 6CBB7DCE6D50-4851-A607-F2EC2C1580C2" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "url": "https://seu-dominio-ou-ip/webhook/evolution",
    "webhook_by_events": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```
