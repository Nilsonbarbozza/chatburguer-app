import os
import aiofiles
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("DataLakeWriter")

class DataLakeWriter:
    """
    Camada 3.7: Output Dinâmico e Manifesto LGPD.
    Processa saídas massivas para JSONL com appending assíncrono superrápido.
    """
    
    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    async def write_jsonl(self, job_id: str, payload_list: list[Dict[str, Any]]):
        """
        Salva o conjunto processado em formato JSON Line appendável.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(self.output_dir, f"{job_id}_{today}.jsonl")
        
        try:
            async with aiofiles.open(file_path, mode='a', encoding='utf-8') as f:
                for payload in payload_list:
                    # Garantia Estrita LGPD: O DataClear já executou,
                    # Mas se quiser um failsafe, pode verificar campos vazados.
                    await f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ [{job_id}] Escritos {len(payload_list)} registros em {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Falha de ESCRITA em I/O no Data Lake: {e}")
            return None

    async def write_manifest(self, job_id: str, total_records: int, format_delivered: str = "jsonl", hash_md5: str = "na"):
        """
        Manisfesto descritivo que acompanha a entrega servindo de lastro legal.
        """
        manifest = {
            "job_id": job_id,
            "generated_at": datetime.now().isoformat(),
            "total_records": total_records,
            "formats_delivered": [format_delivered],
            "hash_md5": hash_md5
        }
        
        manifest_path = os.path.join(self.output_dir, f"{job_id}_manifest.json")
        try:
            async with aiofiles.open(manifest_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(manifest, indent=2, ensure_ascii=False))
            logger.info(f"📜 Manifesto de job criado em {manifest_path}")
        except Exception as e:
             logger.error(f"❌ Falha ao criar manifesto: {e}")
