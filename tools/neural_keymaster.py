import argparse
import os
import secrets
import hashlib
import datetime
import asyncio
from dotenv import load_dotenv
import redis
import asyncpg
from rich.console import Console
from rich.table import Table

console = Console()

# Load environment
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://batalhao_admin:batalhao_secret@localhost:5432/batalhao_control').replace('postgres_batalhao', 'localhost')

try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    console.print(f"[bold red]Erro crítico ao conectar no Redis:[/bold red] {e}")
    exit(1)

async def get_db_conn():
    return await asyncpg.connect(POSTGRES_URL)

def generate_key():
    return f"sk_ns_live_{secrets.token_urlsafe(32)}"

def hash_key(api_key):
    return hashlib.sha256(api_key.encode()).hexdigest()

def get_redis_key(api_key):
    # Now expects a raw key, hashes it, then returns the Redis key
    return f"auth:key:{hash_key(api_key)}"

def create_key(name, limit, tier):
    raw_key = generate_key()
    hashed_key = hash_key(raw_key)
    r_key = f"auth:key:{hashed_key}"
    
    r.hset(r_key, mapping={
        "client_name": name,
        "tier": tier,
        "quota_limit": int(limit),
        "quota_used": 0,
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    
    console.print(f"[bold green]Chave Forjada com Sucesso![/bold green]")
    console.print(f"Cliente: [bold]{name}[/bold]")
    console.print(f"API Key: [bold bright_red]{raw_key}[/bold bright_red]")
    console.print("\n[bold red]ATENÇÃO: Copie esta chave agora. Por segurança (Zero-Trust), ela NUNCA mais será exibida.[/bold red]")

def add_credits(api_key, amount):
    r_key = get_redis_key(api_key)
    if not r.exists(r_key):
        console.print("[bold red]Erro: Chave não encontrada.[/bold red]")
        return
    
    current_limit = int(r.hget(r_key, "quota_limit"))
    new_limit = current_limit + amount
    r.hset(r_key, "quota_limit", new_limit)
    
    console.print(f"[bold green]Carga Injetada![/bold green]")
    console.print(f"Novo limite de requisições: [bold]{new_limit}[/bold]")

def get_status(api_key):
    r_key = get_redis_key(api_key)
    data = r.hgetall(r_key)
    
    if not data:
        console.print("[bold red]Erro: Chave não encontrada.[/bold red]")
        return
    
    limit = int(data.get("quota_limit", 0))
    used = int(data.get("quota_used", 0))
    percent = (used / limit * 100) if limit > 0 else 0
    status_str = data.get("status")
    color = "green" if status_str == "active" else "red"
    
    table = Table(title="Raio-X do Cliente")
    table.add_column("Propriedade", style="cyan")
    table.add_column("Valor", style="magenta")
    
    table.add_row("Nome", data.get("client_name"))
    table.add_row("Tier", data.get("tier"))
    table.add_row("Limite", str(limit))
    table.add_row("Uso", f"{used} ({percent:.1f}%)")
    table.add_row("Status", f"[{color}]{status_str}[/{color}]")
    
    console.print(table)

def list_keys():
    keys = r.keys("auth:key:*")
    if not keys:
        console.print("[yellow]Nenhuma chave encontrada na base.[/yellow]")
        return
    
    table = Table(title="Mapa da Base de Clientes (Zero-Trust)")
    table.add_column("Cliente", style="cyan")
    table.add_column("Key Hash (SHA-256)", style="dim", no_wrap=True)
    table.add_column("Tier")
    table.add_column("Uso/Limite")
    table.add_column("Status")
    
    for k in keys:
        data = r.hgetall(k)
        key_hash = k.replace("auth:key:", "")
        limit = data.get("quota_limit", "0")
        used = data.get("quota_used", "0")
        status = data.get("status")
        color = "green" if status == "active" else "red"
        
        table.add_row(
            data.get("client_name", "N/A"),
            f"{key_hash[:12]}...",
            data.get("tier", "N/A"),
            f"{used}/{limit}",
            f"[{color}]{status}[/{color}]"
        )
        
    console.print(table)

async def run_analytics():
    conn = await get_db_conn()
    
    # 1. Top 5 Domínios
    top_domains = await conn.fetch('''
        SELECT target_domain, COUNT(*) as volume 
        FROM commercial_radar 
        GROUP BY target_domain 
        ORDER BY volume DESC 
        LIMIT 5
    ''')
    
    # 2. Taxa de Sucesso (Status 200 vs 403)
    success_stats = await conn.fetch('''
        SELECT 
            status_code, 
            COUNT(*) as count 
        FROM commercial_radar 
        GROUP BY status_code
    ''')
    
    await conn.close()
    
    console.print("\n[bold cyan]Visão Global de Inteligência (Commercial Radar)[/bold cyan]")
    
    if not top_domains:
        console.print("[yellow]Ainda não há dados de telemetria no Radar.[/yellow]")
        return

    table_top = Table(title="Top 5 Domínios Alvo")
    table_top.add_column("Domínio", style="magenta")
    table_top.add_column("Requisições", justify="right")
    
    for row in top_domains:
        table_top.add_row(row['target_domain'], str(row['volume']))
    
    console.print(table_top)
    
    table_stats = Table(title="Desempenho da API (Status Codes)")
    table_stats.add_column("Status", style="bold")
    table_stats.add_column("Volume", justify="right")
    
    for row in success_stats:
        status = row['status_code']
        color = "green" if status == 200 else "red"
        table_stats.add_row(f"[{color}]{status}[/{color}]", str(row['count']))
        
    console.print(table_stats)

async def list_targets(api_key=None, client_name=None):
    conn = await get_db_conn()
    
    query = "SELECT target_domain, endpoint_used, status_code, timestamp FROM commercial_radar"
    params = []
    
    if api_key:
        # Nota: no radar salvamos client_name para facilitar CLI, 
        # mas poderíamos buscar o nome pelo hash se necessário.
        # Aqui vamos buscar por client_name associado à key no Redis.
        r_key = get_redis_key(api_key)
        client_name = r.hget(r_key, "client_name")
        
    if client_name:
        query += " WHERE client_name = $1"
        params.append(client_name)
    
    query += " ORDER BY timestamp DESC LIMIT 10"
    
    rows = await conn.fetch(query, *params)
    await conn.close()
    
    title = f"Visão Sniper: Últimos Alvos de {client_name}" if client_name else "Últimos 10 Alvos Globais"
    table = Table(title=title)
    table.add_column("Data/Hora", style="dim")
    table.add_column("Domínio", style="cyan")
    table.add_column("Endpoint", style="magenta")
    table.add_column("Status")
    
    for row in rows:
        status = row['status_code']
        color = "green" if status == 200 else "red"
        table.add_row(
            row['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
            row['target_domain'],
            row['endpoint_used'],
            f"[{color}]{status}[/{color}]"
        )
        
    console.print(table)

def revoke_key(api_key):
    r_key = get_redis_key(api_key)
    if not r.exists(r_key):
        console.print("[bold red]Erro: Chave não encontrada.[/bold red]")
        return
    
    r.hset(r_key, "status", "revoked")
    console.print(f"[bold yellow]Acesso revogado para a chave.[/bold yellow]")

def main():
    parser = argparse.ArgumentParser(description="Neural Keymaster - Gestão Concierge de Clientes")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Command: create
    create_parser = subparsers.add_parser("create", help="Forjar uma nova chave de cliente")
    create_parser.add_argument("--name", required=True, help="Nome da empresa/cliente")
    create_parser.add_argument("--limit", required=True, type=int, help="Limite de requisições")
    create_parser.add_argument("--tier", default="enterprise", help="Tier do cliente (default: enterprise)")

    # Command: add_credits
    add_parser = subparsers.add_parser("add_credits", help="Adicionar créditos a um cliente existente")
    add_parser.add_argument("--key", required=True, help="API Key do cliente")
    add_parser.add_argument("--amount", required=True, type=int, help="Quantidade de créditos a injetar")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Ver o Raio-X de um cliente")
    status_parser.add_argument("--key", required=True, help="API Key do cliente")

    # Command: list
    subparsers.add_parser("list", help="Listar todos os clientes")

    # Command: analytics
    subparsers.add_parser("analytics", help="Ver visão global de inteligência de domínios")

    # Command: list-targets
    targets_parser = subparsers.add_parser("list-targets", help="Ver os últimos alvos de um cliente")
    targets_parser.add_argument("--key", help="API Key do cliente")
    targets_parser.add_argument("--name", help="Nome do cliente")

    # Command: revoke
    revoke_parser = subparsers.add_parser("revoke", help="Cortar o acesso de um cliente")
    revoke_parser.add_argument("--key", required=True, help="API Key do cliente")

    args = parser.parse_args()

    if args.command == "create":
        create_key(args.name, args.limit, args.tier)
    elif args.command == "add_credits":
        add_credits(args.key, args.amount)
    elif args.command == "status":
        get_status(args.key)
    elif args.command == "list":
        list_keys()
    elif args.command == "analytics":
        asyncio.run(run_analytics())
    elif args.command == "list-targets":
        asyncio.run(list_targets(api_key=args.key, client_name=args.name))
    elif args.command == "revoke":
        revoke_key(args.key)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
