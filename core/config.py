import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    TAVILY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # Infrastructure
    REDIS_URL: str = "redis://localhost:6379"
    POSTGRES_URL: str = ""
    
    # Limits & Timeouts
    MAX_FILE_SIZE_MB: int = 30
    MAX_IMAGE_SIZE_MB: int = 5
    REQUEST_TIMEOUT: int = 20
    PLAYWRIGHT_TIMEOUT: int = 30000
    
    # Directories
    OUTPUT_DIR: str = "data/output"
    
    # Binaries
    PRETTIER_BIN: str = "prettier"
    LIGHTNINGCSS_BIN: str = "lightningcss"
    PURGECSS_BIN: str = "purgecss"
    NODE_BIN: str = "node"
    
    # Pipeline Behavior
    BUNDLE_SCRIPTS: bool = True
    USE_PRETTIER: bool = True
    USE_LIGHTNINGCSS: bool = True
    USE_PURGECSS: bool = True
    USE_TAILWIND: bool = False
    MINIFY_CSS: bool = False
    LIGHTNINGCSS_TARGETS: str = ">= 0.5%"
    
    # Concurrency
    BATALHAO_CONCURRENCY_L0: int = 20
    BATALHAO_CONCURRENCY_L12: int = 15
    BATALHAO_CONCURRENCY_L34: int = 5

    class Config:
        env_file = None       # CRÍTICO: desliga .env em produção (ECS/Fargate)
        case_sensitive = True

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy loader para as configurações."""
    return Settings()

settings = get_settings()

def get_paths() -> dict:
    """Retorna os caminhos derivados do OUTPUT_DIR atual."""
    out     = settings.OUTPUT_DIR
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


