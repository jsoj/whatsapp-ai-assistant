#!/bin/bash
set -e

# ==============================================================================
# Script de Instalação Automática 1-Click: WhatsApp AI Assistant 2.0 (Antigravity)
# ==============================================================================

echo "🚀 [1/6] Iniciando configuração do WhatsApp AI Assistant..."

# 1. Diretório do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 2. Verifica Python3 e Venv
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instalando python3 e python3-venv..."
    apt-get update && apt-get install -y python3 python3-venv python3-pip
fi

# 3. Cria Ambiente Virtual se não existir
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 [2/6] Criando ambiente virtual Python em $PROJECT_DIR/venv..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# 4. Instala Dependências
echo "📦 [3/6] Instalando dependências do Python..."
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt" pytest gtts

# 5. Configuração do .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚙️ [4/6] Criando arquivo .env a partir do .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
else
    echo "⚙️ [4/6] Arquivo .env existente preservado."
fi

# 6. Criação do Serviço Systemd
echo "🔧 [5/6] Instalando serviço systemd 'whatsapp-assistant.service'..."
cat << SERVICE_EOF > /etc/systemd/system/whatsapp-assistant.service
[Unit]
Description=WhatsApp AI Assistant (Antigravity Engine)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8055
Restart=always
RestartSec=5
LimitNOFILE=65536
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable --now whatsapp-assistant.service
systemctl restart whatsapp-assistant.service

# 7. Regra de Firewall UFW (Permite Docker interno na porta 8055)
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    ufw allow from 10.0.0.0/8 to any port 8055 proto tcp comment 'Allow internal docker to whatsapp-assistant' || true
fi

# 8. Teste de Saúde
echo "🔍 [6/6] Verificando status do serviço..."
sleep 2

HEALTH_CHECK=$(curl -s http://127.0.0.1:8055/health || echo "FAIL")
if [[ "$HEALTH_CHECK" == *"antigravity-agent"* || "$HEALTH_CHECK" == *"ok"* ]]; then
    echo "================================================================================"
    echo "✅ WHATSAPP AI ASSISTANT INSTALADO E OPERACIONAL COM SUCESSO!"
    echo "================================================================================"
    echo "📍 Endpoint Local: http://127.0.0.1:8055"
    echo "📍 Healthcheck:    http://127.0.0.1:8055/health"
    echo "📍 Webhook URL:    https://<seu-dominio>/webhook/evolution"
    echo "⚙️ Logs ao vivo:   journalctl -u whatsapp-assistant -f"
    echo "================================================================================"
else
    echo "⚠️ Aviso: O serviço iniciou mas o healthcheck retornou: $HEALTH_CHECK"
    echo "Verifique os logs com: journalctl -u whatsapp-assistant -n 20"
fi
