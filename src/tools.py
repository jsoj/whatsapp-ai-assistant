import os
import subprocess
import smtplib
import socket
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from src.config import settings

COOLIFY_TOKEN = "2|mf6o2yxxzzrN9oCNvpEMYyXhgVGFC4OjHb473gPX8722264c"
COOLIFY_API_URL = "http://72.61.135.23:8000/api/v1"

def send_email(to_email: str, subject: str, body: str, sender_alias: str = "contato@projetobrasil2050.site") -> str:
    """
    Envia um e-mail para o destinatário especificado usando o servidor SMTP Mailcow da VPS.
    
    Args:
        to_email: Endereço de e-mail do destinatário.
        subject: Assunto do e-mail.
        body: Conteúdo da mensagem.
        sender_alias: Endereço de e-mail do remetente (ex: contato@projetobrasil2050.site, contato@fersie.com, contato@institutoagrogen.com).
    """
    smtp_host = os.getenv("SMTP_HOST", "72.61.135.23")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", sender_alias)
    smtp_pass = os.getenv("SMTP_PASS", "")

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_alias
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

        return f"✅ E-mail enviado com sucesso para {to_email} (Assunto: '{subject}')."
    except Exception as e:
        print(f"❌ [Email Tool Error]: {e}")
        return f"Erro ao enviar e-mail para {to_email}: {e}"

def execute_command(command: str) -> str:
    """
    Executa um comando de terminal Linux/bash no servidor e retorna o resultado da execução.
    
    Args:
        command: O comando de terminal bash a ser executado (ex: 'uptime', 'docker ps', 'df -h', 'git status').
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=45
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "Comando executado com sucesso sem saída."
    except Exception as e:
        return f"Erro ao executar o comando '{command}': {e}"

def read_file_content(file_path: str) -> str:
    """
    Lê e retorna o conteúdo de um arquivo de texto no sistema de arquivos da VPS.
    
    Args:
        file_path: Caminho absoluto ou relativo do arquivo (ex: '/home/jsoj/.gemini/config/AGENTS.md').
    """
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"Arquivo não encontrado: {file_path}"
        if path.stat().st_size > 500_000:
            return f"Arquivo muito grande ({path.stat().st_size} bytes) para leitura direta."
        content = path.read_text(encoding="utf-8", errors="replace")
        return content[:10_000]
    except Exception as e:
        return f"Erro ao ler arquivo '{file_path}': {e}"

def write_file_content(file_path: str, content: str) -> str:
    """
    Cria ou atualiza um arquivo de texto no sistema de arquivos.
    
    Args:
        file_path: Caminho do arquivo a ser criado/editado.
        content: Conteúdo em texto a ser gravado no arquivo.
    """
    try:
        path = Path(file_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"✅ Arquivo '{file_path}' gravado com sucesso ({len(content)} caracteres)."
    except Exception as e:
        return f"Erro ao gravar arquivo '{file_path}': {e}"

def manage_coolify(action: str, resource_uuid: str = "") -> str:
    """
    Gerencia aplicações e serviços na VPS através da API do Coolify.
    
    Args:
        action: Ação a ser executada ('list_apps', 'list_services', 'deploy', 'restart', 'logs', 'status').
        resource_uuid: UUID da aplicação ou serviço (ex: 'p5j5vt794we07gdju05fxej4' ou 'ldx3g6q997326vd4bxh79tor').
    """
    headers = {"Authorization": f"Bearer {COOLIFY_TOKEN}"}
    try:
        if action in ["list_apps", "apps"]:
            resp = httpx.get(f"{COOLIFY_API_URL}/applications", headers=headers, timeout=15)
            apps = resp.json()
            summary = [f"- {a.get('name')} (UUID: {a.get('uuid')}, Status: {a.get('status')}, FQDN: {a.get('fqdn')})" for a in apps]
            return "Aplicações no Coolify:\n" + "\n".join(summary)
        
        elif action in ["list_services", "services"]:
            resp = httpx.get(f"{COOLIFY_API_URL}/services", headers=headers, timeout=15)
            services = resp.json()
            summary = [f"- {s.get('name')} (UUID: {s.get('uuid')}, Status: {s.get('status')})" for s in services]
            return "Serviços no Coolify:\n" + "\n".join(summary)
        
        elif action == "deploy" and resource_uuid:
            resp = httpx.get(f"{COOLIFY_API_URL}/deploy?uuid={resource_uuid}", headers=headers, timeout=15)
            return f"🚀 Deploy acionado para {resource_uuid}: {resp.text}"

        elif action == "restart" and resource_uuid:
            resp = httpx.post(f"{COOLIFY_API_URL}/applications/{resource_uuid}/restart", headers=headers, timeout=15)
            if resp.status_code != 200:
                resp = httpx.post(f"{COOLIFY_API_URL}/services/{resource_uuid}/restart", headers=headers, timeout=15)
            return f"🔄 Reinício acionado para {resource_uuid}: {resp.text}"

        elif action == "logs" and resource_uuid:
            resp = httpx.get(f"{COOLIFY_API_URL}/applications/{resource_uuid}/logs?count=40", headers=headers, timeout=15)
            return f"Logs de {resource_uuid}:\n" + resp.text[:4000]

        elif action == "status" and resource_uuid:
            resp = httpx.get(f"{COOLIFY_API_URL}/applications/{resource_uuid}", headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return f"Status de {data.get('name')}: {data.get('status')} (FQDN: {data.get('fqdn')})"
            resp = httpx.get(f"{COOLIFY_API_URL}/services/{resource_uuid}", headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return f"Status do serviço {data.get('name')}: {data.get('status')}"
            return f"Recurso {resource_uuid} não encontrado."

        return "Ação inválida ou UUID ausente. Use 'list_apps', 'list_services', 'deploy', 'restart', 'status' ou 'logs'."
    except Exception as e:
        return f"Erro na integração com Coolify: {e}"

def check_domain_dns(domain: str) -> str:
    """
    Verifica o status de resolução DNS e IP de um domínio do usuário.
    
    Args:
        domain: O nome do domínio a ser verificado (ex: 'projetobrasil2050.site', 'arteemvender.com', 'fersie.com').
    """
    clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    try:
        ip = socket.gethostbyname(clean_domain)
        return f"🌐 Domínio '{clean_domain}' resolvendo para o IP: {ip}"
    except Exception as e:
        return f"❌ Não foi possível resolver o domínio '{clean_domain}': {e}"

def get_system_status() -> str:
    """
    Retorna métricas completas de uso de CPU, RAM, Disco e containers Docker na VPS Hostinger.
    """
    try:
        uptime_res = subprocess.run("uptime", shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
        mem_res = subprocess.run("free -h", shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
        disk_res = subprocess.run("df -h /", shell=True, capture_output=True, text=True, timeout=10).stdout.strip()
        docker_res = subprocess.run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'", shell=True, capture_output=True, text=True, timeout=10).stdout.strip()

        report = (
            f"📊 Status do Sistema VPS Hostinger:\n\n"
            f"⏱ Uptime: {uptime_res}\n\n"
            f"🧠 Memória RAM:\n{mem_res}\n\n"
            f"💾 Disco /:\n{disk_res}\n\n"
            f"🐳 Containers Docker Ativos:\n{docker_res[:1500]}"
        )
        return report
    except Exception as e:
        return f"Erro ao obter status do sistema: {e}"

def query_git_repository(repo_path: str = "/home/jsoj/dev/whatsapp-ai-assistant", command: str = "status") -> str:
    """
    Consulta ou executa comandos git em um repositório do projeto.
    
    Args:
        repo_path: Caminho do repositório no sistema de arquivos.
        command: Subcomando git (ex: 'status', 'log -n 5', 'branch', 'pull').
    """
    try:
        full_cmd = f"git -C {repo_path} {command}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip() or result.stderr.strip()
        return output or "Comando git executado com sucesso."
    except Exception as e:
        return f"Erro ao executar git '{command}' em '{repo_path}': {e}"

# Mapeamento completo de ferramentas executáveis autonomamente pelo Gemini
AVAILABLE_TOOLS = [
    send_email,
    execute_command,
    read_file_content,
    write_file_content,
    manage_coolify,
    check_domain_dns,
    get_system_status,
    query_git_repository
]
