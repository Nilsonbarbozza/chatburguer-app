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
        from core.config import get_paths
        paths = get_paths()
        out = result.get('output', {})
        stats = {}

        html_file = out.get('html_file')
        if html_file and os.path.exists(html_file):
            stats['html_size'] = f"{os.path.getsize(html_file) / 1024:.1f}KB"

        css_file = out.get('css_file')
        if css_file and os.path.exists(css_file):
            orig_size = os.path.getsize(css_file)
            stats['css_size'] = f"{orig_size / 1024:.1f}KB"

            # Estatísticas do Shadow Build
            safe_css = paths['SAFE_STYLE_FILE']
            if os.path.exists(safe_css):
                safe_size = os.path.getsize(safe_css)
                reduction = (1 - safe_size / orig_size) * 100 if orig_size > 0 else 0
                stats['shadow_css_size'] = f"{safe_size / 1024:.1f}KB"
                stats['reduction'] = f"{reduction:.1f}%"
                stats['tester_file'] = paths['TESTER_FILE']

        images_dir = out.get('images_dir')
        if images_dir and os.path.isdir(images_dir):
            images = list(Path(images_dir).iterdir())
            stats['image_count'] = len(images)

        js_bundle = out.get('js_bundle')
        if js_bundle and os.path.exists(js_bundle):
            stats['js_size'] = f"{os.path.getsize(js_bundle) / 1024:.1f}KB"

        return stats
