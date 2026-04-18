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
        force = '--force' in args
        Updater().check_and_update(token=token, force=force)
        sys.exit(0)

    if '--logout' in args:
        from cli.auth import TokenAuth
        TokenAuth().clear_token()
        print("✅ Token removido. Execute 'cloner' para fazer login novamente.")
        sys.exit(0)

    # Modo direto: cloner --url https://... [--file caminho.html] [--mode web|dataset] [--no-redact]
    if '--url' in args or '--file' in args:
        url = None
        file = None
        mode = 'web'
        redact = True
        strict = False # Poda Semântica de Elite
        
        if '--url' in args:
            uidx = args.index('--url')
            url = args[uidx + 1] if uidx + 1 < len(args) else None
            
        if '--file' in args:
            fidx = args.index('--file')
            file = args[fidx + 1] if fidx + 1 < len(args) else None

        if '--mode' in args:
            midx = args.index('--mode')
            mode = args[midx + 1] if midx + 1 < len(args) else 'web'
            
        if '--no-redact' in args:
            redact = False

        if '--strict' in args:
            strict = True
            
        if not url and not file:
            print("Uso: cloner --url https://site.com [--file local.html] [--mode web|dataset] [--strict]")
            sys.exit(1)
            
        _run_direct(file_path=file, url=url, mode=mode, redact=redact, strict=strict)
        return

    # Modo interativo padrão
    from cli.interface import ClonerCLI
    ClonerCLI().run()


def _run_direct(file_path: str = None, url: str = None, mode: str = 'web', redact: bool = True, strict: bool = False):
    """Executa o pipeline sem prompts interativos."""
    from cli.auth     import TokenAuth, AuthError
    from core.pipeline import build_pipeline
    from core.config   import update_output_dir
    import json

    # Configuração de Logs p/ Console (Compatibilidade Windows Total)
    def safe_print(msg, emoji=""):
        # Mapeamento de emojis para ASCII se falhar
        mapping = {
            "✅": "[OK]",
            "❌": "[ERRO]",
            "✨": "[JSON]",
            "🧠": "[SKILL]",
            "⚠️": "[AVISO]",
            "→": "-> "
        }
        clean_msg = msg.replace("→", "->")
        try:
            print(f"{emoji} {clean_msg}")
        except UnicodeEncodeError:
            print(f"{mapping.get(emoji, '[*]')} {clean_msg}")

    try:
        TokenAuth().ensure_authenticated()
    except AuthError as e:
        safe_print(f"Erro: {e}", "❌")
        sys.exit(1)

    update_output_dir('output')
    pipeline = build_pipeline(mode=mode, redact_pii=redact, strict=strict)

    try:
        result = pipeline.execute({
            'input_file': file_path,
            'url': url
        })
        if mode == 'dataset':
            jsonl_path = result.get('dataset_path')
            readable_path = result.get('dataset_readable_path')
            
            if not jsonl_path:
                jsonl_path = os.path.join('output', 'dataset.jsonl')
            
            safe_print(f"Dataset Concluido -> {jsonl_path}", "✅")
            if readable_path:
                safe_print(f"Versao Legivel  -> {readable_path}", "✨")
        else:
            out = result.get('output', {})
            safe_print(f"Concluido -> {out.get('html_file', 'index.html')}", "✅")
            if result.get('skill_file'):
                safe_print(f"Skill     -> {result['skill_file']}", "🧠")
    except Exception as e:
        safe_print(f"Erro: {e}", "❌")
        sys.exit(1)


if __name__ == '__main__':
    main()
