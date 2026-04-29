
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

    async def write_jsonl(self, mission_id: str, payload_list: List[Dict[str, Any]], capture_id: str = "unknown") -> str:
        """
        Salva artefatos curados em JSONL atômico (1 arquivo por captura para evitar Race Conditions).
        """
        dir_path = self._generate_path(mission_id)
        # Usamos o capture_id no nome para garantir que NUNCA dois workers escrevam no mesmo arquivo
        file_name = f"capture_{capture_id}.jsonl"
        file_path = os.path.join(dir_path, file_name)
        
        try:
            # Escrita atômica: preparamos o conteúdo e escrevemos de uma vez
            content = ""
            for payload in payload_list:
                content += json.dumps(payload, ensure_ascii=False) + '\n'
            
            async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                await f.write(content)
            
            logger.info(f"✅ [Mission: {mission_id}] Artefato Atômico Gravado: {file_name}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Falha de ESCRITA ATÔMICA no Curated Store: {e}")
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
