import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Configuração Padrão do Postgres
# Se rodar fora do docker, postgres_batalhao deve ser localhost
POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://batalhao_admin:batalhao_secret@localhost:5432/batalhao_control').replace('postgres_batalhao', 'localhost')

class DatabaseManager:
    """
    Gerenciador unificado de conexão PostgreSQL.
    Focado em telemetria e auditoria de missões.
    """
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(POSTGRES_URL)

    async def save_radar_log(self, client_name: str, domain: str, endpoint: str, status_code: int):
        """
        Salva um registro no Radar Comercial de forma assíncrona.
        """
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO commercial_radar (client_name, target_domain, endpoint_used, status_code)
                VALUES ($1, $2, $3, $4)
            ''', client_name, domain, endpoint, status_code)

    async def close(self):
        if self.pool:
            await self.pool.close()

# Instância global compartilhada
db = DatabaseManager()
