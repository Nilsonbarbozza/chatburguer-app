"""
cli/updater.py
Sistema de auto-atualização — cloner --update
"""
import os
import sys
import json
import hashlib
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

import requests

CURRENT_VERSION = "1.0.2"
API_BASE_URL    = os.getenv('CLONER_API_URL', 'https://chatburguer-server.onrender.com')
INSTALL_DIR     = Path(__file__).parent.parent
REQUEST_TIMEOUT = 10


class Updater:
    def __init__(self):
        self.current = CURRENT_VERSION

    def check_and_update(self, token: Optional[str] = None, force: bool = False) -> bool:
        try:
            from rich.console import Console
            console = Console()
            _rich = True
        except ImportError:
            _rich = False
            console = None

        def info(msg):
            if _rich: console.print(f"[cyan]{msg}[/cyan]")
            else: print(msg)

        def ok(msg):
            if _rich: console.print(f"[green]✅ {msg}[/green]")
            else: print(f"✅ {msg}")

        def warn(msg):
            if _rich: console.print(f"[yellow]⚠  {msg}[/yellow]")
            else: print(f"⚠  {msg}")

        info("Verificando atualizações...")
        try:
            resp = requests.get(
                f"{API_BASE_URL}/v1/version",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': f'Chatburguer/{self.current}'}
            )
            resp.raise_for_status()
            data         = resp.json()
            latest       = data.get('version', self.current)
            download_url = data.get('download_url')
            expected_sha = data.get('sha256')
            changelog    = data.get('changelog', '')
        except Exception as e:
            warn(f"Não foi possível verificar atualizações: {e}")
            return False

        if not force and not self._is_newer(latest, self.current):
            ok(f"Você já tem a versão mais recente ({self.current})")
            return False

        if _rich:
            console.print(f"\n[bold]Nova versão:[/bold] {self.current} → [green]{latest}[/green]")
            if changelog:
                console.print(f"[dim]{changelog}[/dim]")
            from rich.prompt import Confirm
            if not Confirm.ask("Atualizar agora?", default=True):
                return False
        else:
            print(f"\nNova versão: {self.current} → {latest}")
            if input("Atualizar? [S/n]: ").strip().lower() not in ('', 's', 'y'):
                return False

        info("Baixando atualização...")
        if token:
            download_url = f"{download_url}?token={token}"

        try:
            r = requests.get(download_url, timeout=60, stream=True,
                             headers={'User-Agent': f'Chatburguer/{self.current}'})
            r.raise_for_status()
            if not expected_sha:
                expected_sha = r.headers.get('X-SHA256')
        except Exception as e:
            warn(f"Falha no download: {e}")
            return False

        tmp_zip = tempfile.mktemp(suffix='.zip')
        sha = hashlib.sha256()
        with open(tmp_zip, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                sha.update(chunk)

        if expected_sha and sha.hexdigest() != expected_sha:
            os.unlink(tmp_zip)
            warn("Falha na verificação de integridade.")
            return False
        ok("Integridade verificada")

        info("Aplicando atualização...")
        try:
            backup_dir = str(INSTALL_DIR) + f"_backup_{self.current}"
            shutil.copytree(INSTALL_DIR, backup_dir, dirs_exist_ok=True)

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                tmp_dir = tempfile.mkdtemp()
                zf.extractall(tmp_dir)
                entries = os.listdir(tmp_dir)
                src_dir = os.path.join(tmp_dir, entries[0]) if len(entries) == 1 and \
                          os.path.isdir(os.path.join(tmp_dir, entries[0])) else tmp_dir

                preserve = {'.env', 'config.json'}
                for item in Path(src_dir).rglob('*'):
                    rel = item.relative_to(src_dir)
                    if rel.name in preserve:
                        continue
                    dest = INSTALL_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if item.is_file():
                        shutil.copy2(item, dest)

            shutil.rmtree(tmp_dir, ignore_errors=True)
            os.unlink(tmp_zip)
            shutil.rmtree(backup_dir, ignore_errors=True)

        except Exception as e:
            warn(f"Erro ao aplicar atualização: {e}")
            return False

        ok(f"Chatburguer atualizado para v{latest}!")
        if _rich:
            console.print("[dim]Reinicie o programa para usar a nova versão.[/dim]")
        return True

    def _is_newer(self, latest: str, current: str) -> bool:
        def parse(v):
            try:
                return tuple(int(x) for x in v.strip('v').split('.'))
            except Exception:
                return (0, 0, 0)
        return parse(latest) > parse(current)