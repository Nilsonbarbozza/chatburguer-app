"""
core/utils.py
Utilitários compartilhados entre os stages do pipeline
"""
import os
import re
import base64
import hashlib
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger('html_processor')

try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False


def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    logger.info(f"Diretórios criados: {', '.join(dirs)}")


def save_file(path: str, content: Any, mode: str = 'w', is_bytes: bool = False):
    try:
        write_mode = mode + ('b' if is_bytes else '')
        encoding   = None if is_bytes else 'utf-8'
        with open(path, write_mode, encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Arquivo salvo: {path}")
    except Exception as e:
        logger.error(f"Erro ao salvar {path}: {e}")
        raise


def safe_b64decode(data: str) -> Optional[bytes]:
    try:
        data = re.sub(r'[^A-Za-z0-9+/=]', '', data.strip())
        pad  = len(data) % 4
        if pad:
            data += '=' * (4 - pad)
        return base64.b64decode(data)
    except Exception as e:
        logger.warning(f"Erro ao decodificar base64: {e}")
        return None


def tool_available(binary: str) -> bool:
    return shutil.which(binary) is not None


def run_command(cmd: List[str], stdin: str = None, timeout: int = 30) -> Optional[str]:
    try:
        if cmd and cmd[0]:
            cmd[0] = shutil.which(cmd[0]) or cmd[0]

        result = subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout,
            shell=(os.name == 'nt')
        )
        if result.returncode == 0:
            return result.stdout
        else:
            err_msg = (result.stderr or "").strip()
            logger.warning(f"Comando {cmd[0]} retornou {result.returncode}. Erro: {err_msg[:300]}")
            return None
    except FileNotFoundError:
        logger.warning(f"Binário não encontrado: {cmd[0]}")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout ao executar: {cmd[0]}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado em run_command({cmd[0]}): {e}")
        return None


def setup_logging() -> logging.Logger:
    logger_inst = logging.getLogger('html_processor')
    if logger_inst.handlers:
        return logger_inst

    logger_inst.setLevel(logging.DEBUG)

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(log_level)  # terminal level

    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler('logs/processor.log', encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(fmt)
    fh.setFormatter(fmt)
    logger_inst.addHandler(ch)
    logger_inst.addHandler(fh)
    return logger_inst
