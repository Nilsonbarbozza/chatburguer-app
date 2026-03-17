"""
cli/uploader.py
Resolução de caminhos de arquivo — suporte a drag-and-drop no terminal
"""
import os
import re
from pathlib import Path
from typing import Optional


class FileUploader:
    """
    Resolve caminhos de arquivo enviados pelo usuário.
    Suporta:
      - Caminho absoluto: /Users/fulano/Downloads/site.html
      - Caminho relativo: ../site.html
      - Drag-and-drop no terminal (pode gerar aspas ou escape de espaços)
      - Windows com barras invertidas: C:\\Users\\...
    """

    def resolve(self, raw_path: str) -> Optional[str]:
        path = self._clean(raw_path)

        # Tenta como está
        if os.path.isfile(path):
            return os.path.abspath(path)

        # Tenta expandir home (~)
        expanded = os.path.expanduser(path)
        if os.path.isfile(expanded):
            return os.path.abspath(expanded)

        # Windows: converte barras
        win_path = path.replace('\\', '/')
        if os.path.isfile(win_path):
            return os.path.abspath(win_path)

        return None

    def _clean(self, raw: str) -> str:
        """Remove aspas, escapes e espaços extras."""
        raw = raw.strip()

        # Remove aspas simples ou duplas ao redor
        raw = re.sub(r"""^['"]|['"]$""", '', raw)

        # Remove escape de espaços (drag-and-drop Linux/Mac): /path/to/my\ file.html
        raw = raw.replace('\\ ', ' ')

        return raw.strip()

    def is_html(self, path: str) -> bool:
        ext = Path(path).suffix.lower()
        return ext in ('.html', '.htm', '.xhtml')
