"""
core/config.py
Configuração centralizada — carrega .env e expõe CONFIG + paths dinâmicos
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    'MAX_FILE_SIZE_MB':  int(os.getenv('MAX_FILE_SIZE_MB', 30)),
    'MAX_IMAGE_SIZE_MB': int(os.getenv('MAX_IMAGE_SIZE_MB', 5)),
    'REQUEST_TIMEOUT':   int(os.getenv('REQUEST_TIMEOUT', 30)),
    'OUTPUT_DIR':        os.getenv('OUTPUT_DIR', 'output'),
    'INDENT_SIZE':       int(os.getenv('INDENT_SIZE', 2)),

    # Ferramentas externas
    'PRETTIER_BIN':      os.getenv('PRETTIER_BIN', 'prettier'),
    'LIGHTNINGCSS_BIN':  os.getenv('LIGHTNINGCSS_BIN', 'lightningcss'),
    'PURGECSS_BIN':      os.getenv('PURGECSS_BIN', 'purgecss'),
    'NODE_BIN':          os.getenv('NODE_BIN', 'node'),

    # Comportamento
    'BUNDLE_SCRIPTS':       os.getenv('BUNDLE_SCRIPTS',    'true').lower()  == 'true',
    'USE_PRETTIER':         os.getenv('USE_PRETTIER',      'true').lower()  == 'true',
    'USE_LIGHTNINGCSS':     os.getenv('USE_LIGHTNINGCSS',  'true').lower()  == 'true',
    'USE_PURGECSS':         os.getenv('USE_PURGECSS',      'true').lower()  == 'true',
    'USE_TAILWIND':         os.getenv('USE_TAILWIND',      'false').lower() == 'true',
    'LIGHTNINGCSS_TARGETS': os.getenv('LIGHTNINGCSS_TARGETS', '>= 0.5%'),
    'MINIFY_CSS':           os.getenv('MINIFY_CSS',        'false').lower() == 'true',
    'MINIFY_LEVEL':         os.getenv('MINIFY_LEVEL',      'extreme'),
    'ALWAYS_GENERATE_TESTER': os.getenv('ALWAYS_GENERATE_TESTER', 'true').lower() == 'true',

    # Validação Visual (Shadow Health Check)
    'USE_VALIDATION':        os.getenv('USE_VALIDATION', 'true').lower() == 'true',
    'VALIDATION_THRESHOLD':  float(os.getenv('VALIDATION_THRESHOLD', 0.05)), # Tolerância de 5% de pixels diferentes
    'PLAYWRIGHT_TIMEOUT':    int(os.getenv('PLAYWRIGHT_TIMEOUT', 30000)),
}


def update_output_dir(path: str):
    """Atualiza OUTPUT_DIR em runtime (usado pela CLI)."""
    CONFIG['OUTPUT_DIR'] = path


def get_paths() -> dict:
    """Retorna os caminhos derivados do OUTPUT_DIR atual."""
    out     = CONFIG['OUTPUT_DIR']
    styles  = os.path.join(out, 'styles')
    images  = os.path.join(out, 'images')
    videos  = os.path.join(out, 'videos')
    scripts = os.path.join(out, 'scripts')
    skills  = os.path.join(out, 'skills')
    return {
        'OUT_DIR':         out,
        'STYLES_DIR':      styles,
        'IMAGES_DIR':      images,
        'VIDEOS_DIR':      videos,
        'SCRIPTS_DIR':     scripts,
        'SKILLS_DIR':      skills,
        'STYLE_FILE':      os.path.join(styles,  'styles.css'),
        'SAFE_STYLE_FILE': os.path.join(styles,  'styles.safe.css'),
        'BUNDLE_FILE':     os.path.join(scripts, 'main.js'),
        'TESTER_FILE':     os.path.join(out,     'tester.html'),
        'SKILL_FILE':      os.path.join(skills,  'frontend.md'),
    }

