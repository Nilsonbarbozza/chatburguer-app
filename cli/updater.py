"""
cli/updater.py
Sistema de auto-atualização — cloner --update
Verifica a versão no servidor e atualiza o programa se necessário.
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

CURRENT_VERSION = "1.0.1"
API_BASE_URL    = os.getenv('CLONER_API_URL', 'https://chatburguer.com')
INSTALL_DIR     = Path(__file__).parent.parent   # raiz do processo-cloner
REQUEST_TIMEOUT = 10


class Updater:
    def __init__(self):
        self.current = CURRENT_VERSION

    def check_and_update(self, token: Optional[str] = None, force: bool = False) -> bool:
        """
        Verifica se há atualização e aplica se necessário.
        Retorna True se atualizou, False se já estava na versão mais recente.
        """
        try:
            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, TextColumn
            console = Console()
            _rich   = True
        except ImportError:
            _rich   = False
            console = None

        def info(msg):
            if _rich: console.print(f"[cyan]{msg}[/cyan]")
            else:     print(msg)

        def ok(msg):
            if _rich: console.print(f"[green]✅ {msg}[/green]")
            else:     print(f"✅ {msg}")

        def warn(msg):
            if _rich: console.print(f"[yellow]⚠  {msg}[/yellow]")
            else:     print(f"⚠  {msg}")

        # 1. Consulta versão disponível
        info("Verificando atualizações...")
        try:
            resp = requests.get(
                f"{API_BASE_URL}/v1/version",
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': f'ProcessCloner/{self.current}'}
            )
            resp.raise_for_status()
            data          = resp.json()
            latest        = data.get('version', self.current)
            download_url  = data.get('download_url')
            expected_sha  = data.get('sha256')
            changelog     = data.get('changelog', '')
        except Exception as e:
            warn(f"Não foi possível verificar atualizações: {e}")
            return False

        # 2. Compara versões
        if not force and not self._is_newer(latest, self.current):
            ok(f"Você já tem a versão mais recente ({self.current})")
            return False

        if _rich:
            console.print(f"\n[bold]Nova versão disponível:[/bold] {self.current} → [green]{latest}[/green]")
            if changelog:
                console.print(f"[dim]{changelog}[/dim]")
            from rich.prompt import Confirm
            if not Confirm.ask("Atualizar agora?", default=True):
                return False
        else:
            print(f"\nNova versão: {self.current} → {latest}")
            if input("Atualizar? [S/n]: ").strip().lower() not in ('', 's', 'y'):
                return False

        # 3. Baixa o ZIP
        info("Baixando atualização...")
        headers = {'User-Agent': f'ProcessCloner/{self.current}'}
        if token:
            download_url = f"{download_url}?token={token}"

        try:
            r = requests.get(download_url, timeout=60, stream=True, headers=headers)
            r.raise_for_status()
            # Usa hash do header se disponível
            if not expected_sha:
                expected_sha = r.headers.get('X-SHA256')
        except Exception as e:
            warn(f"Falha no download: {e}")
            return False

        # 4. Salva temporariamente
        tmp_zip = tempfile.mktemp(suffix='.zip')
        sha = hashlib.sha256()
        with open(tmp_zip, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                sha.update(chunk)

        # 5. Verifica integridade
        actual_sha = sha.hexdigest()
        if expected_sha and actual_sha != expected_sha:
            os.unlink(tmp_zip)
            warn("Falha na verificação de integridade. Atualização cancelada.")
            return False
        ok("Integridade verificada")

        # 6. Aplica atualização (extrai sobre o diretório atual)
        info("Aplicando atualização...")
        try:
            backup_dir = str(INSTALL_DIR) + f"_backup_{self.current}"
            shutil.copytree(INSTALL_DIR, backup_dir, dirs_exist_ok=True)

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                # Extrai para temp, depois move
                tmp_dir = tempfile.mkdtemp()
                zf.extractall(tmp_dir)

                # Descobre se tem subpasta
                entries = os.listdir(tmp_dir)
                src_dir = os.path.join(tmp_dir, entries[0]) if len(entries) == 1 and \
                          os.path.isdir(os.path.join(tmp_dir, entries[0])) else tmp_dir

                # Copia os arquivos novos (preserva .env e config do usuário)
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

            # Remove backup antigo se sucesso
            shutil.rmtree(backup_dir, ignore_errors=True)

        except Exception as e:
            warn(f"Erro ao aplicar atualização: {e}")
            warn(f"Backup disponível em: {backup_dir}")
            return False

        ok(f"Process Cloner atualizado para v{latest}!")
        if _rich:
            console.print("[dim]Reinicie o programa para usar a nova versão.[/dim]")
        return True

    def _is_newer(self, latest: str, current: str) -> bool:
        """Compara versões semânticas X.Y.Z"""
        def parse(v):
            try:
                return tuple(int(x) for x in v.strip('v').split('.'))
            except Exception:
                return (0, 0, 0)
        return parse(latest) > parse(current)
