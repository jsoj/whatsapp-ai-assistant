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

def query_git_repository(repo_path: str = "/root/whatsapp-ai-assistant", command: str = "status") -> str:
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

def registrar_gasto_pessoal(
    valor: float,
    categoria: str,
    descricao: str,
    forma_pagamento: str = "PIX",
    data: str = "",
    tag: str = ""
) -> str:
    """
    Registra fisicamente um gasto pessoal na tabela de Gastos_Pessoais.md dentro do Cofre (VPS2/notes).
    
    Args:
        valor: Valor numérico do gasto em Reais (ex: 85.50).
        categoria: Categoria do gasto (ex: 'Refeição', 'Carro', 'Moradia / Casa', 'Saúde', 'Educação', 'Outros').
        descricao: Descrição detalhada da despesa.
        forma_pagamento: Forma de pagamento utilizada (ex: 'PIX', 'Cartão de Crédito', 'Débito', 'Dinheiro').
        data: Data no formato AAAA-MM-DD (se vazio, usa a data atual).
        tag: Tag identificadora de origem (ex: '[Grupo Casal]').
    """
    from datetime import datetime
    date_str = data.strip() if data and data.strip() else datetime.now().strftime("%Y-%m-%d")
    gastos_path = Path("/home/jsoj/VPS2/notes/03_Pessoal/Gastos_Pessoais.md")
    clean_tag = tag.strip()
    full_desc = f"{clean_tag} {descricao.strip()}".strip() if clean_tag and not descricao.strip().startswith(clean_tag) else descricao.strip()
    try:
        if not gastos_path.exists():
            return f"Erro: Arquivo do Cofre não encontrado em {gastos_path}"

        content = gastos_path.read_text(encoding="utf-8")
        new_row = f"| {date_str} | {categoria.strip()} | {full_desc} | {float(valor):.2f} | {forma_pagamento.strip()} |"

        lines = content.splitlines()
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("|") and ("Data" in line or ":---" in line or "202" in line):
                insert_idx = i + 1

        lines.insert(insert_idx, new_row)
        gastos_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return (
            f"✅ *Despesa registrada no Cofre (`Gastos_Pessoais.md`):*\n"
            f"• *Data:* {date_str}\n"
            f"• *Valor:* R$ {float(valor):.2f}\n"
            f"• *Categoria:* {categoria.strip()}\n"
            f"• *Descrição:* {full_desc}\n"
            f"• *Forma de Pagamento:* {forma_pagamento.strip()}"
        )
    except Exception as e:
        return f"Erro ao registrar gasto no Cofre: {e}"

def gerar_relatorio_gastos(mes: str = "", tag: str = "") -> str:
    """
    Gera um relatório e gráfico consolidado das despesas em Gastos_Pessoais.md com totais por categoria.
    
    Args:
        mes: Filtro de mês no formato AAAA-MM (ex: '2026-10'). Se vazio, considera todas as despesas ou o mês corrente.
        tag: Filtro opcional por tag (ex: '[Grupo Casal]').
    """
    gastos_path = Path("/home/jsoj/VPS2/notes/03_Pessoal/Gastos_Pessoais.md")
    if not gastos_path.exists():
        return "Erro: Gastos_Pessoais.md não encontrado."
    
    lines = gastos_path.read_text(encoding="utf-8").splitlines()
    rows = []
    for line in lines:
        if line.startswith("|") and not ("Data" in line or ":---" in line or "Categoria" in line):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 4:
                try:
                    val = float(parts[3])
                    rows.append({
                        "data": parts[0],
                        "categoria": parts[1],
                        "descricao": parts[2],
                        "valor": val,
                        "pagamento": parts[4] if len(parts) > 4 else "PIX"
                    })
                except ValueError:
                    continue
    
    filtered = rows
    if mes:
        filtered = [r for r in filtered if r["data"].startswith(mes)]
    if tag:
        filtered = [r for r in filtered if tag.lower() in r["descricao"].lower()]

    if not filtered:
        return f"📊 Nenhum gasto registrado para o filtro (Mês: {mes or 'todos'}, Tag: {tag or 'todas'})."

    total = sum(r["valor"] for r in filtered)
    by_cat = {}
    for r in filtered:
        by_cat[r["categoria"]] = by_cat.get(r["categoria"], 0.0) + r["valor"]

    sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    report = [f"📊 *Relatório de Gastos — {mes or 'Geral'}*"]
    if tag:
        report.append(f"🏷️ *Origem:* `{tag}`")
    report.append(f"💰 *Total Acumulado:* R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    report.append("\n📈 *Distribuição por Categoria:*")

    for cat, val in sorted_cats:
        pct = (val / total) * 100 if total > 0 else 0
        bars_count = int(pct / 10)
        bar = "█" * bars_count + "░" * (10 - bars_count)
        val_str = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        report.append(f"• *{cat}*: {val_str} ({pct:.1f}%)\n  `[{bar}]`")

    return "\n".join(report)

def gerenciar_agenda_e_casa(
    acao: str,
    item_ou_evento: str = "",
    quem: str = "",
    data: str = "",
    horario: str = "",
    detalhes: str = ""
) -> str:
    """
    Gerencia a agenda de compromissos familiares, lista de compras e manutenções no Cofre (Agenda_e_Compras.md).
    
    Args:
        acao: 'adicionar_evento', 'listar_agenda', 'adicionar_compra', 'listar_compras', 'adicionar_manutencao', 'listar_manutencao'.
        item_ou_evento: Nome do evento/compromisso, item de compra ou reparo.
        quem: Pessoa envolvida (ex: 'Sophia', 'Julia', 'Sibele', 'Junior', 'Família').
        data: Data no formato AAAA-MM-DD. Se vazio, usa data atual.
        horario: Horário do compromisso (ex: '14:30', '19:00').
        detalhes: Local, observações ou notas adicionais.
    """
    from datetime import datetime
    agenda_path = Path("/home/jsoj/VPS2/notes/04_Vida_Familiar_e_Casa/Agenda_e_Compras.md")
    if not agenda_path.exists():
        return "Erro: Arquivo Agenda_e_Compras.md não encontrado."
    
    content = agenda_path.read_text(encoding="utf-8")
    date_str = data.strip() if data and data.strip() else datetime.now().strftime("%Y-%m-%d")
    
    if acao == "adicionar_evento":
        row = f"| {date_str} | {horario.strip() or 'A definir'} | {item_ou_evento.strip()} | {quem.strip() or 'Família'} | {detalhes.strip()} |"
        lines = content.splitlines()
        idx = len(lines)
        for i, l in enumerate(lines):
            if "Agenda de Compromissos" in l:
                idx = i + 3
                break
        lines.insert(idx, row)
        agenda_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"📅 *Compromisso registrado na Agenda da Família!*\n• *Data:* {date_str} às {horario or 'horário a combinar'}\n• *Evento:* {item_ou_evento}\n• *Quem:* {quem or 'Família'}\n• *Local/Notas:* {detalhes or '-'}"

    elif acao == "listar_agenda":
        lines = content.splitlines()
        events = [l for l in lines if l.startswith("|") and not ("Data" in l or ":---" in l or "Item" in l)]
        if not events:
            return "📅 Nenhum compromisso agendado no momento."
        return "📅 *Próximos Compromissos da Família:*\n" + "\n".join(events[:8])

    elif acao == "adicionar_compra":
        row = f"| {item_ou_evento.strip()} | {detalhes.strip() or 'Geral'} | {quem.strip() or 'Família'} | Pendente |"
        lines = content.splitlines()
        idx = len(lines)
        for i, l in enumerate(lines):
            if "Lista de Compras" in l:
                idx = i + 3
                break
        lines.insert(idx, row)
        agenda_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"🛒 *Item adicionado à lista de compras:* `{item_ou_evento}` ({detalhes or 'Geral'})\nSolicitado por: {quem or 'Família'}"

    elif acao == "listar_compras":
        lines = content.splitlines()
        in_compras = False
        items = []
        for l in lines:
            if "Lista de Compras" in l:
                in_compras = True
                continue
            if in_compras:
                if l.startswith("## ") or l.startswith("---"):
                    if items:
                        break
                elif l.startswith("|") and not ("Item" in l or ":---" in l):
                    items.append(l)
        if not items:
            return "🛒 A lista de compras está vazia no momento!"
        return "🛒 *Lista de Compras Pendentes:*\n" + "\n".join(items)

    elif acao == "adicionar_manutencao":
        row = f"| {item_ou_evento.strip()} | {detalhes.strip() or 'Casa'} | {quem.strip() or 'Família'} | Pendente |"
        lines = content.splitlines()
        idx = len(lines)
        for i, l in enumerate(lines):
            if "Manutenção Residencial" in l:
                idx = i + 3
                break
        lines.insert(idx, row)
        agenda_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"🛠️ *Tarefa de manutenção anotada:* `{item_ou_evento}` ({detalhes or 'Casa'})"

    return f"Ação '{acao}' não reconhecida."

def estacionar_ideia_trilho(
    ideia: str,
    contexto: str = "Geral",
    onde_executar: str = "VPS / Notebook",
    prioridade: str = "Média"
) -> str:
    """
    Estaciona uma ideia ou tarefa paralela no Parking Lot (Estacionamento de Digressões)
    dos arquivos FOCUS.md e TRILHO_FOCO.md para não perder o foco da Missão Ativa.
    
    Args:
        ideia: A ideia, lembrete ou tarefa a ser estacionada.
        contexto: Cartucho ou área (ex: 'contexto-laboratorio', 'contexto-pessoal', 'contexto-produtiva', 'Infra VPS').
        onde_executar: Ambiente alvo (ex: 'VPS Hostinger', 'Notebook Arch Linux', 'Notebook Windows').
        prioridade: Nível de prioridade ('Alta', 'Média', 'Baixa').
    """
    import re
    targets = [
        Path("/root/context/FOCUS.md"),
        Path("/home/jsoj/VPS2/notes/05_Atividades_e_Rotina/TRILHO_FOCO.md")
    ]
    updated_files = []
    clean_idea = ideia.strip().replace("|", "-")

    for path in targets:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            in_parking = False
            last_table_idx = -1
            max_num = 0

            for i, line in enumerate(lines):
                if "ESTACIONAMENTO DE DIGRESSÕES" in line:
                    in_parking = True
                    continue
                if in_parking:
                    if line.strip().startswith("|"):
                        last_table_idx = i
                        m = re.match(r"^\|\s*\*?\*?(\d+)\*?\*?\s*\|", line.strip())
                        if m:
                            max_num = max(max_num, int(m.group(1)))
                    elif last_table_idx != -1 and line.strip().startswith("---"):
                        break

            next_num = max_num + 1
            new_row = f"| **{next_num}** | `{contexto.strip()}` | {clean_idea} | {onde_executar.strip()} | {prioridade.strip()} |"
            if last_table_idx != -1:
                lines.insert(last_table_idx + 1, new_row)
            else:
                lines.append(new_row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            updated_files.append(path.name)
        except Exception as e:
            print(f"⚠️ Erro ao atualizar {path}: {e}")

    if updated_files:
        return (
            f"🅿️ *Ideia estacionada com sucesso!* ({', '.join(updated_files)})\n"
            f"• *Item #{next_num}:* {clean_idea}\n"
            f"• *Contexto:* `{contexto}` | *Prioridade:* {prioridade}\n\n"
            f"🛤️ _Foco mantido na Missão Única Ativa._"
        )
    return "⚠️ Não foi possível localizar os arquivos do Trilho de Foco."

def consultar_cofre_notas(atalho_ou_termo: str = "INDEX.md") -> str:
    """
    Lê notas rápidas ou busca por um termo nos arquivos Markdown do Cofre (VPS2/notes).
    
    Args:
        atalho_ou_termo: Nome do atalho ('index', 'foco', 'trilho', 'gastos', 'financeiro_iag', 'saude', 'tarefas')
                         ou caminho/termo para buscar dentro de /home/jsoj/VPS2/notes.
    """
    notes_root = Path("/home/jsoj/VPS2/notes")
    shortcuts = {
        "index": notes_root / "INDEX.md",
        "index.md": notes_root / "INDEX.md",
        "foco": Path("/root/context/FOCUS.md"),
        "trilho": notes_root / "05_Atividades_e_Rotina/TRILHO_FOCO.md",
        "gastos": notes_root / "03_Pessoal/Gastos_Pessoais.md",
        "financeiro_iag": notes_root / "01_Profissional/IAG_Instituto_Agro_Genetica/Financeiro_IAG.md",
        "iag": notes_root / "01_Profissional/IAG_Instituto_Agro_Genetica/Financeiro_IAG.md",
        "saude": notes_root / "03_Pessoal/Saude.md",
        "tarefas": notes_root / "05_Atividades_e_Rotina/Atividades_e_Tarefas.md",
    }
    key = atalho_ou_termo.strip().lower()
    if key in shortcuts and shortcuts[key].exists():
        return shortcuts[key].read_text(encoding="utf-8", errors="replace")[:8000]

    candidate = notes_root / atalho_ou_termo.strip().lstrip("/")
    if candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8", errors="replace")[:8000]

    # Busca por nome ou conteúdo nos arquivos .md do Cofre
    matches = []
    for md_file in notes_root.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            if key in md_file.name.lower() or key in text.lower():
                rel = md_file.relative_to(notes_root)
                matches.append(f"📄 *{rel}*:\n{text[:1500]}")
        except Exception:
            continue
    if matches:
        return "\n\n---\n\n".join(matches[:4])
    return f"Nenhuma nota encontrada no Cofre para '{atalho_ou_termo}'."

def consultar_emails_aura(conta: str = "gmail_agromarkers", termo_busca: str = "", limite: int = 5) -> str:
    """
    Consulta ou busca e-mails recentes nas caixas de correio da AURA (IMAP).
    
    Args:
        conta: Identificador da conta:
               'gmail_agromarkers' (contato@agromarkers.com.br - Instituto Agro Genética/IAG),
               'gmail_pessoal' (junior31maio@gmail.com),
               'icloud_pessoal' (jsoj@me.com).
        termo_busca: Palavra-chave opcional para filtrar remetente ou assunto (ex: 'BASF', 'Laudo', 'Nota', 'Fatura'). Se vazio, lista os últimos recebidos.
        limite: Quantidade máxima de mensagens para retornar (padrão 5).
    """
    import sys
    sys.path.append("/root/context/scripts")
    try:
        from aura_email_engine import list_or_search_emails
        res = list_or_search_emails(account_key=conta, query=termo_busca if termo_busca.strip() else None, limit=limite)
        if not res:
            return f"📭 Nenhum e-mail encontrado na conta `{conta}`" + (f" com o termo '{termo_busca}'." if termo_busca else ".")
        
        output = [f"📬 *Últimos e-mails ({conta})*:"]
        for m in res:
            dt = m.get("date", "").split(" +")[0].split(" -")[0]
            output.append(
                f"• *Assunto:* {m.get('subject')}\n"
                f"  *De:* {m.get('from')}\n"
                f"  *Data:* {dt}\n"
                f"  *Prévia:* {m.get('snippet', '')[:180].replace(chr(10), ' ')}...\n"
            )
        return "\n".join(output)
    except Exception as e:
        return f"Erro ao consultar e-mails da AURA ({conta}): {e}"

def enviar_email_aura(conta: str = "gmail_agromarkers", para: str = "", assunto: str = "", corpo: str = "") -> str:
    """
    Envia um e-mail através da conta oficial da AURA (SMTP autenticado).
    
    Args:
        conta: 'gmail_agromarkers' (contato@agromarkers.com.br) ou 'gmail_pessoal' (junior31maio@gmail.com).
        para: Endereço de e-mail do destinatário.
        assunto: Assunto do e-mail.
        corpo: Texto do corpo do e-mail.
    """
    import sys
    sys.path.append("/root/context/scripts")
    try:
        from aura_email_engine import send_email_message
        res = send_email_message(account_key=conta, to_addr=para, subject=assunto, body=corpo)
        return f"✅ E-mail enviado com sucesso de `{res.get('from')}` para `{para}`! (Assunto: '{assunto}')"
    except Exception as e:
        return f"Erro ao enviar e-mail via AURA ({conta}): {e}"

def consultar_omie_iag(modulo: str, filtro: str = "", pagina: int = 1, solicitante: str = "", chat_origem: str = "") -> str:
    """
    Consulta o ERP Omie do Instituto Agro Genética (IAG).
    
    Regras de Governança & Segurança (RBAC Estrito):
    - Apenas permitido no chat privado do Junior (Owner) ou dentro do grupo IAG Sócios (120363423519539092@g.us).
    - Proibido qualquer acesso fora destes dois canais.
    - Se o usuário for o Junior: Acesso total (módulos permitidos, contas_a_receber, contas_a_pagar, estoque, etc.).
    - Se for outro usuário no grupo IAG Sócios: Escopo limitado estritamente a 'contas_a_pagar', 'contas_a_receber' e 'estoque'.
    - SALVAGUARDA CRÍTICA: Saldos bancários e aplicações de contas correntes NUNCA são expostos a terceiros.
    
    Args:
        modulo: 'contas_a_receber', 'contas_a_pagar' ou 'estoque'.
        filtro: Nome do cliente, fornecedor ou produto para filtrar (opcional).
        pagina: Página de registros (padrão 1).
        solicitante: Telefone/JID de quem fez a pergunta (injetado internamente).
        chat_origem: JID do grupo ou chat onde foi solicitada a consulta.
    """
    # Validação de Canal Permitido: Apenas Privado do Junior ou Grupo IAG Sócios
    is_iag_group = "120363423519539092" in str(chat_origem)
    is_owner = any(owner in str(solicitante) or str(solicitante) in owner for owner in settings.owner_numbers) if solicitante else False

    # Se chat_origem estiver vazio, verifica se ao menos quem chamou é owner
    if not is_owner and not is_iag_group:
        return "⛔ [Salvaguarda Omie]: O acesso aos dados do ERP Omie é estritamente restrito ao canal privado do Administrador e ao Grupo IAG Sócios."

    app_key = os.getenv("OMIE_APP_KEY", "")
    app_secret = os.getenv("OMIE_APP_SECRET", "")
    
    if not app_key or not app_secret:
        return (
            "⚠️ [Omie IAG]: As credenciais de API do Omie (OMIE_APP_KEY e OMIE_APP_SECRET) "
            "ainda não foram localizadas no ambiente do servidor. Peça ao Junior para configurá-las."
        )

    modulo_clean = str(modulo).strip().lower()
    headers = {"Content-Type": "application/json"}
    
    # Se não for o Junior, limitar rigidamente aos 3 módulos permitidos
    if not is_owner:
        if modulo_clean not in ["contas_a_receber", "receber", "recebimento", "contas_a_pagar", "pagar", "pagamento", "estoque", "produtos", "reagentes"]:
            return "⛔ [Salvaguarda IAG]: Para membros do grupo, o acesso ao Omie é restrito a: Contas a Pagar, Contas a Receber e Estoque."

    try:
        if modulo_clean in ["contas_a_receber", "receber", "recebimento"]:
            endpoint = "https://app.omie.com.br/api/v1/financas/contareceber/"
            call = "ListarContasReceber"
            param = {
                "pagina": pagina,
                "registros_por_pagina": 20,
                "apenas_importado_api": "N"
            }
            if filtro:
                param["filtrar_por_cliente"] = filtro

        elif modulo_clean in ["contas_a_pagar", "pagar", "pagamento"]:
            endpoint = "https://app.omie.com.br/api/v1/financas/contapagar/"
            call = "ListarContasPagar"
            param = {
                "pagina": pagina,
                "registros_por_pagina": 20,
                "apenas_importado_api": "N"
            }
            if filtro:
                param["filtrar_por_fornecedor"] = filtro

        elif modulo_clean in ["estoque", "produtos", "reagentes"]:
            endpoint = "https://app.omie.com.br/api/v1/estoque/consultaestoque/"
            call = "ListarPosEstoque"
            param = {
                "pagina": pagina,
                "registros_por_pagina": 20
            }
        else:
            return f"⚠️ Módulo Omie desconhecido: '{modulo}'. Use 'contas_a_receber', 'contas_a_pagar' ou 'estoque'."

        body = {
            "app_key": app_key,
            "app_secret": app_secret,
            "call": call,
            "param": [param]
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(endpoint, json=body, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return f"✅ [Omie IAG - {call}]: {json.dumps(data, ensure_ascii=False)[:3000]}"
            else:
                return f"❌ Erro Omie ({resp.status_code}): {resp.text}"

    except Exception as e:
        return f"❌ Erro ao consultar Omie IAG: {e}"

# Mapeamento completo de ferramentas executáveis autonomamente pelo Gemini
AVAILABLE_TOOLS = [
    send_email,
    execute_command,
    read_file_content,
    write_file_content,
    manage_coolify,
    check_domain_dns,
    get_system_status,
    query_git_repository,
    registrar_gasto_pessoal,
    gerar_relatorio_gastos,
    gerenciar_agenda_e_casa,
    estacionar_ideia_trilho,
    consultar_cofre_notas,
    consultar_emails_aura,
    enviar_email_aura,
    consultar_omie_iag,
]

# Ferramentas permitidas para membros do grupo IAG (fora o Junior)
IAG_GROUP_TOOLS = [
    consultar_omie_iag,
    consultar_cofre_notas,
    check_domain_dns,
    get_system_status,
]

# Ferramentas permitidas para o grupo Família/Casa (fora o Junior)
FAMILY_GROUP_TOOLS = [
    registrar_gasto_pessoal,
    gerar_relatorio_gastos,
    gerenciar_agenda_e_casa,
    consultar_cofre_notas,
]

def get_tools_for_request(chat_target: str, sender_digits: str) -> list:
    """
    Aplica RBAC estrito para ferramentas:
    - Junior (Owner): Acesso a TODAS as ferramentas.
    - Grupo IAG: Apenas ferramentas de consulta IAG (Omie, notas públicas, status).
    - Grupo Família/Casa: Apenas ferramentas financeiras domésticas e agenda da casa.
    - Qualquer outro terceiro: Lista vazia (apenas conversa/LLM puro sem ferramentas).
    """
    is_owner = any(owner in sender_digits or sender_digits in owner for owner in settings.owner_numbers)
    if is_owner:
        return AVAILABLE_TOOLS

    # Se for membro em grupo autorizado
    if "120363423519539092" in chat_target:  # Grupo IAG
        return IAG_GROUP_TOOLS
    elif "120363147621109705" in chat_target or "120363064087395658" in chat_target:  # Grupos Casal e Casa
        return FAMILY_GROUP_TOOLS

    return []
