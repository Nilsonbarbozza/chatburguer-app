
import os
import json
import asyncio
import aiofiles
import hashlib
import gzip
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

class RawArtifactStore:
    """
    Raw Capture Plane Storage (Enterprise Edition).
    Suporta compressão GZIP e organização hierárquica por data/missão.
    """
    def __init__(self, base_path: str = "data/raw", compress: bool = True):
        self.base_path = base_path
        self.compress = compress
        os.makedirs(base_path, exist_ok=True)

    def _generate_path(self, mission_id: str) -> str:
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

    async def save_artifact(self, mission_id: str, capture_id: str, 
                              content: str, metadata: Dict[str, Any]) -> Tuple[str, str]:
        """
        Persiste o conteúdo bruto (com compressão opcional) e metadados.
        """
        dir_path = self._generate_path(mission_id)
        
        # 1. Salva Conteúdo Bruto
        ext = "html" if metadata.get("content_type", "").lower() == "text/html" else "txt"
        if self.compress: ext += ".gz"
        
        raw_filename = f"{capture_id}.{ext}"
        raw_path = os.path.join(dir_path, raw_filename)
        
        if self.compress:
            # GZIP é síncrono no Python standard, usamos thread pool para não travar o loop
            def _write_gz():
                with gzip.open(raw_path, 'wt', encoding='utf-8') as f:
                    f.write(content)
            await asyncio.to_thread(_write_gz)
        else:
            async with aiofiles.open(raw_path, mode='w', encoding='utf-8') as f:
                await f.write(content)
        
        # 2. Salva Metadados Técnicos
        meta_filename = f"{capture_id}.meta.json"
        meta_path = os.path.join(dir_path, meta_filename)
        
        async with aiofiles.open(meta_path, mode='w', encoding='utf-8') as f:
            # Enriquecendo metadados com info de compressão
            metadata["storage"] = {
                "compressed": self.compress,
                "format": "gzip" if self.compress else "plain",
                "path": raw_path
            }
            await f.write(json.dumps(metadata, indent=2))
            
        return f"file://{raw_path}", f"file://{meta_path}"

    async def load_content(self, raw_uri: str) -> str:
        """Carrega e descomprime (se necessário) o conteúdo do storage."""
        if not raw_uri.startswith("file://"):
            raise ValueError(f"URI de storage não suportada: {raw_uri}")
            
        path = raw_uri.replace("file://", "")
        
        if path.endswith(".gz"):
            def _read_gz():
                with gzip.open(path, 'rt', encoding='utf-8') as f:
                    return f.read()
            return await asyncio.to_thread(_read_gz)
        else:
            async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                return await f.read()

    @staticmethod
    def calculate_hash(content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
