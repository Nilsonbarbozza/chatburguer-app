#!/usr/bin/env python3
"""
Process Cloner v1.0
Entry point da CLI — suporta flags:
  cloner              → modo interativo
  cloner --update     → verifica e aplica atualização
  cloner --version    → exibe versão
  cloner --logout     → remove token salvo
  cloner --file PATH  → processa diretamente sem prompt
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cli.updater import CURRENT_VERSION


def main():
    args = sys.argv[1:]

    if '--version' in args or '-v' in args:
        print(f"Process Cloner v{CURRENT_VERSION}")
        sys.exit(0)

    if '--update' in args:
        from cli.updater import Updater
        from cli.auth    import TokenAuth
        token = TokenAuth().get_saved_token()
        Updater().check_and_update(token=token)
        sys.exit(0)

    if '--logout' in args:
        from cli.auth import TokenAuth
        TokenAuth().clear_token()
        print("✅ Token removido. Execute 'cloner' para fazer login novamente.")
        sys.exit(0)

    # Modo direto: cloner --file caminho.html [--url https://...]
    if '--file' in args:
        idx  = args.index('--file')
        file = args[idx + 1] if idx + 1 < len(args) else None
        url  = None
        if '--url' in args:
            uidx = args.index('--url')
            url  = args[uidx + 1] if uidx + 1 < len(args) else None
        if not file:
            print("Uso: cloner --file caminho/para/arquivo.html [--url https://site.com]")
            sys.exit(1)
        _run_direct(file, url)
        return

    # Modo interativo padrão
    from cli.interface import ClonerCLI
    ClonerCLI().run()


def _run_direct(file_path: str, base_url: str = None):
    """Executa o pipeline sem prompts interativos."""
    from cli.auth     import TokenAuth, AuthError
    from core.pipeline import build_pipeline
    from core.config   import update_output_dir

    try:
        TokenAuth().ensure_authenticated()
    except AuthError as e:
        print(f"❌ {e}")
        sys.exit(1)

    update_output_dir('output')
    pipeline = build_pipeline()

    try:
        result = pipeline.execute({'input_file': file_path, 'base_url': base_url})
        out = result['output']
        print(f"✅ Concluído → {out['html_file']}")
        if result.get('skill_file'):
            print(f"🧠 Skill     → {result['skill_file']}")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
