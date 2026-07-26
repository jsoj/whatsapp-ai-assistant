import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from src.config import settings

def send_email(to_email: str, subject: str, body: str) -> str:
    """
    Envia um e-mail para o destinatário especificado usando o servidor SMTP Mailcow.
    
    Args:
        to_email: Endereço de e-mail do destinatário.
        subject: Assunto do e-mail.
        body: Conteúdo do e-mail.
    """
    smtp_host = os.getenv("SMTP_HOST", "72.61.135.23")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "contato@projetobrasil2050.site")
    smtp_pass = os.getenv("SMTP_PASS", "")
    sender_email = os.getenv("SMTP_SENDER", smtp_user or "contato@projetobrasil2050.site")

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if smtp_pass:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            try:
                with smtplib.SMTP(smtp_host, 25, timeout=15) as server:
                    server.send_message(msg)
            except Exception:
                with smtplib.SMTP("localhost", 25, timeout=15) as server:
                    server.send_message(msg)

        return f"E-mail enviado com sucesso para {to_email} com o assunto '{subject}'."
    except Exception as e:
        print(f"❌ [Email Tool Error]: {e}")
        return f"Erro ao enviar e-mail para {to_email}: {e}"

def execute_command(command: str) -> str:
    """
    Executa um comando no terminal Linux do ambiente e retorna a saída.
    
    Args:
        command: O comando bash a ser executado.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "Comando executado com sucesso."
    except Exception as e:
        return f"Erro ao executar o comando '{command}': {e}"

def deploy_coolify_application(app_uuid: str) -> str:
    """
    Aciona o re-deploy de uma aplicação no Coolify através da API.
    
    Args:
        app_uuid: O UUID da aplicação no Coolify.
    """
    url = f"http://72.61.135.23:8000/api/v1/deploy?uuid={app_uuid}"
    headers = {"Authorization": "Bearer 2|mf6o2yxxzzrN9oCNvpEMYyXhgVGFC4OjHb473gPX8722264c"}
    try:
        resp = httpx.get(url, headers=headers, timeout=15)
        return f"Deploy da aplicação {app_uuid} iniciado no Coolify: {resp.text}"
    except Exception as e:
        return f"Erro ao acionar deploy no Coolify: {e}"

# Mapeamento de ferramentas disponíveis para execução autônoma
AVAILABLE_TOOLS = [
    send_email,
    execute_command,
    deploy_coolify_application
]
