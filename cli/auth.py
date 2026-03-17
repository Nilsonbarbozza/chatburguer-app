"""
cli/auth.py
Sistema de autenticação por token.
Valida o token do usuário contra o servidor do Chatburguer
antes de permitir qualquer processamento.
"""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

import requests

# ── Configuração ──────────────────────────────────────────
# Troque pela URL do seu servidor quando for ao ar
API_BASE_URL  = os.getenv('CLONER_API_URL', 'https://chatburguer.com')
CONFIG_DIR    = Path.home() / '.process-cloner'
CONFIG_FILE   = CONFIG_DIR / 'config.json'
REQUEST_TIMEOUT = 8   # segundos

# Cache local: evita validar o token a cada clone (valida 1x por hora)
CACHE_TTL_SECONDS = 3600


class AuthError(Exception):
    """Erro de autenticação — token inválido, expirado ou sem conexão."""
    pass


class TokenAuth:
    """
    Gerencia o ciclo de vida do token do usuário:
      - Armazenamento local seguro (~/.process-cloner/config.json)
      - Validação online contra o servidor
      - Cache local para evitar requests desnecessários
    """

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────────────
    # API pública
    # ─────────────────────────────────────────────

    def ensure_authenticated(self) -> Dict[str, Any]:
        """
        Garante que o usuário tem um token válido antes de continuar.
        Fluxo:
          1. Lê token salvo localmente
          2. Se não tem → pede ao usuário
          3. Valida no servidor
          4. Salva localmente se válido
        Retorna o payload do usuário: { user, plan, clones_used, clones_limit }
        Lança AuthError em caso de falha.
        """
        token = self._load_token()

        if not token:
            token = self._prompt_token()

        user_data = self._validate_online(token)

        # Salva token + cache
        self._save_config(token, user_data)
        return user_data

    def get_saved_token(self) -> Optional[str]:
        """Retorna o token salvo sem validar."""
        return self._load_token()

    def clear_token(self):
        """Remove o token salvo (logout)."""
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()

    def show_status(self) -> Optional[Dict[str, Any]]:
        """Retorna dados do usuário se token válido, None caso contrário."""
        token = self._load_token()
        if not token:
            return None
        try:
            return self._validate_online(token)
        except AuthError:
            return None

    # ─────────────────────────────────────────────
    # Internos
    # ─────────────────────────────────────────────

    def _load_token(self) -> Optional[str]:
        """Lê o token do arquivo de configuração local."""
        if not CONFIG_FILE.exists():
            return None
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            return data.get('token')
        except Exception:
            return None

    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Retorna cache se ainda válido (dentro do TTL)."""
        if not CONFIG_FILE.exists():
            return None
        try:
            data  = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            cache = data.get('cache', {})
            ts    = cache.get('timestamp', 0)
            if time.time() - ts < CACHE_TTL_SECONDS:
                return cache.get('user_data')
        except Exception:
            pass
        return None

    def _save_config(self, token: str, user_data: Dict[str, Any]):
        """Salva token + cache localmente."""
        config = {
            'token': token,
            'cache': {
                'timestamp': time.time(),
                'user_data': user_data,
            }
        }
        CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding='utf-8')
        # Permissão restrita no Unix (só o dono lê)
        try:
            CONFIG_FILE.chmod(0o600)
        except Exception:
            pass

    def _prompt_token(self) -> str:
        """Solicita o token ao usuário no terminal."""
        try:
            from rich.console import Console
            from rich.prompt  import Prompt
            console = Console()
            console.print()
            console.print("[bold cyan]🔑 Ativação do Chatburguer[/bold cyan]")
            console.print("[dim]Você precisa de um token para usar o Chatburguer.[/dim]")
            console.print("[dim]Adquira em: [bold]chatburguer.com[/bold][/dim]")
            console.print()
            token = Prompt.ask("[cyan]Cole seu token aqui[/cyan]").strip()
        except ImportError:
            print("\n🔑 Ativação do Chatburguer")
            print("  Insira seu token de acesso (adquira em chatburguer.com):")
            token = input("  Token: ").strip()

        if not token:
            raise AuthError("Nenhum token informado.")
        return token

    def _validate_online(self, token: str) -> Dict[str, Any]:
        """
        Valida o token contra o servidor.
        Fluxo:
          1. Verifica cache válido (TTL 1h) → retorna direto
          2. Tenta validar online
          3. Se offline → verifica grace period (24h após último sucesso)
          4. Se servidor retorna 401/403 → bloqueia imediatamente
        """
        GRACE_PERIOD = 86400  # 24 horas em segundos

        # 1. Cache válido (dentro de 1h)
        cached = self._load_cache()
        if cached:
            return cached

        try:
            resp = requests.post(
                f"{API_BASE_URL}/v1/validate-token",
                json={'token': token},
                timeout=REQUEST_TIMEOUT,
                headers={
                    'User-Agent': 'ProcessCloner/1.0',
                    'Content-Type': 'application/json',
                }
            )
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                Exception) as e:
            # 3. OFFLINE — usa grace period
            return self._handle_offline(token, GRACE_PERIOD, str(e))

        # 4. Servidor respondeu — trata cada status
        if resp.status_code == 200:
            return resp.json().get('user', {})

        if resp.status_code == 401:
            self.clear_token()
            raise AuthError(
                "Token inválido. Verifique o token enviado no seu email de compra.\n"
                "  Suporte: suporte@chatburguer.com"
            )

        if resp.status_code == 403:
            raise AuthError(
                "Token expirado ou assinatura inativa.\n"
                "  Renove em: chatburguer.com/renovar"
            )

        if resp.status_code == 429:
            raise AuthError("Muitas tentativas de autenticação. Aguarde 60 segundos.")

        raise AuthError(f"Erro no servidor de autenticação (HTTP {resp.status_code}).")

    def _handle_offline(self, token: str, grace_period: int, err: str) -> Dict[str, Any]:
        """
        Modo offline: permite uso por até grace_period segundos
        após a última validação online bem-sucedida.
        """
        GRACE_PERIOD = grace_period
        if not CONFIG_FILE.exists():
            raise AuthError(
                f"Sem conexão e sem validação anterior.\n"
                f"  Conecte-se à internet para ativar pela primeira vez.\n"
                f"  Detalhe: {err}"
            )

        try:
            data       = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            cache      = data.get('cache', {})
            last_ts    = cache.get('timestamp', 0)
            user_data  = cache.get('user_data', {})
            elapsed    = time.time() - last_ts
            remaining  = max(0, GRACE_PERIOD - elapsed)
            hours_left = int(remaining / 3600)
        except Exception:
            raise AuthError("Não foi possível verificar o token offline.")

        if elapsed > GRACE_PERIOD:
            raise AuthError(
                "Sem conexão com o servidor há mais de 24 horas.\n"
                "  Reconecte-se à internet para continuar usando o Chatburguer."
            )

        # Avisa o usuário que está no grace period
        try:
            from rich.console import Console
            Console().print(
                f"[yellow]⚠  Sem conexão ao servidor — modo offline "
                f"({hours_left}h restantes de {int(GRACE_PERIOD/3600)}h)[/yellow]"
            )
        except ImportError:
            print(f"⚠  Offline — {hours_left}h restantes no grace period")

        return user_data
