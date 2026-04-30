import asyncio
import os
import sys

# Adiciona a raiz do projeto ao path para localizar o 'core' e scripts irmãos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from start.ingest_batalhao import ingest_urls

async def start_massive_invasion():
    # 1. Carrega os links do arquivo
    file_path = "data/output/375_links_ds_academy.txt"
    if not os.path.exists(file_path):
        print(f"❌ Erro: Arquivo {file_path} não encontrado!")
        return

    # Política de Missão Crítica: Prioridade para DS Academy (Blog Archetype)
    mission_config = {
        "archetype": "blog",
        "fidelity_threshold": 0.65,
        "allowed_domains": "blog.dsacademy.com.br",
        "redact_pii": True
    }
    
    print(f"🚀 [INVASÃO] Disparando ingestão massiva no Control Plane...")
    
    await ingest_urls(
        file_path=file_path,
        job_id="missao_ia_375_ds_academy",
        respect_robots=True,
        force_level="auto",
        mission_config=mission_config
    )
    
    print(f"\n✅ Invasão Massiva Iniciada!")
    print(f"Status: Operação catalogada no PostgreSQL. Workers mobilizados.")

if __name__ == "__main__":
    asyncio.run(start_massive_invasion())
