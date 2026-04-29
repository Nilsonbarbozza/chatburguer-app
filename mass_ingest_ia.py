
import asyncio
import os
import logging
from ingest_batalhao import IngestorBatalhao

async def start_massive_invasion():
    # 1. Carrega os links do arquivo
    file_path = "data/output/375_links_ds_academy.txt"
    if not os.path.exists(file_path):
        print(f"❌ Erro: Arquivo {file_path} não encontrado!")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        target_urls = [line.strip() for line in f if line.strip()]

    print(f"🎯 [DS ACADEMY] Carregados {len(target_urls)} alvos de alta fidelidade.")

    ingestor = IngestorBatalhao()
    
    # Política de Missão Crítica: Prioridade para DS Academy (Blog Archetype)
    policy = {
        "respect_robots": True,
        "force_level": "auto",
        "archetype": "blog",
        "fidelity_threshold": 0.65,
        "redact_pii": True,
        "allowed_domains": "blog.dsacademy.com.br"
    }
    
    print(f"🚀 [INVASÃO] Disparando ingestão massiva no Control Plane...")
    
    mission_id = await ingestor.run_ingestion(
        job_id="missao_ia_375_ds_academy",
        urls=target_urls,
        policy=policy
    )
    
    print(f"\n✅ Invasão Massiva Iniciada!")
    print(f"Mission ID: {mission_id}")
    print(f"Alvos Ativos: {len(target_urls)}")
    print(f"Status: Operação catalogada no PostgreSQL. Workers mobilizados.")

if __name__ == "__main__":
    asyncio.run(start_massive_invasion())
