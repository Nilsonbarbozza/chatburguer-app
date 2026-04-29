
import os
import aiofiles
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("DataLakeWriter")

class DataLakeWriter:
    """
    Curated Store Writer.
    Responsável por organizar artefatos homologados em estrutura hierárquica por Missão.
    """
    
    def __init__(self, base_path: str = "data/curated"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        
    def _generate_path(self, mission_id: str) -> str:
        """Gera estrutura curated/YYYY/MM/DD/mission_id/"""
        now = datetime.utcnow()
        path = os.path.join(
            self.base_path,
            now.strftime("%Y"),
            now.strftime("%m"),
            now.strftime("%d"),
            mission_id
        )
        os.makedirs(path, exist_ok=True)
        return path

    async def write_jsonl(self, mission_id: str, payload_list: List[Dict[str, Any]]) -> str:
        """
        Salva artefatos curados em JSONL particionado.
        """
        dir_path = self._generate_path(mission_id)
        file_path = os.path.join(dir_path, "dataset.jsonl")
        
        try:
            async with aiofiles.open(file_path, mode='a', encoding='utf-8') as f:
                for payload in payload_list:
                    await f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            
            logger.info(f"✅ [Mission: {mission_id}] Gravados {len(payload_list)} registros em {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Falha de ESCRITA no Curated Store: {e}")
            return ""

    async def write_manifest(self, mission_id: str, job_id: str, total_records: int):
        """Manifesto de auditoria por missão."""
        dir_path = self._generate_path(mission_id)
        manifest = {
            "mission_id": mission_id,
            "job_id": job_id,
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": total_records,
            "rule_version": "v3_standard"
        }
        
        manifest_path = os.path.join(dir_path, "manifest.json")
        async with aiofiles.open(manifest_path, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(manifest, indent=2, ensure_ascii=False))
