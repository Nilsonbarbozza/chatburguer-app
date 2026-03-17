"""
cli/reporter.py
Geração de relatório pós-processamento
"""
import os
from pathlib import Path
from typing import Dict, Any


class Reporter:
    def summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna dicionário com estatísticas do processamento."""
        out = result.get('output', {})
        stats = {}

        html_file = out.get('html_file')
        if html_file and os.path.exists(html_file):
            stats['html_size'] = f"{os.path.getsize(html_file) / 1024:.1f}KB"

        css_file = out.get('css_file')
        if css_file and os.path.exists(css_file):
            stats['css_size'] = f"{os.path.getsize(css_file) / 1024:.1f}KB"

        images_dir = out.get('images_dir')
        if images_dir and os.path.isdir(images_dir):
            images = list(Path(images_dir).iterdir())
            stats['image_count'] = len(images)

        js_bundle = out.get('js_bundle')
        if js_bundle and os.path.exists(js_bundle):
            stats['js_size'] = f"{os.path.getsize(js_bundle) / 1024:.1f}KB"

        return stats
