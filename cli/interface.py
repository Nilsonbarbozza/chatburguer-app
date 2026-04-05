"""
cli/interface.py
Interface principal da CLI — banner, fluxo interativo, barra de progresso
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from cli.uploader import FileUploader
from cli.reporter import Reporter
from cli.auth     import TokenAuth, AuthError

console = Console() if RICH_AVAILABLE else None


BANNER = r"""
  ██████╗ ██╗      ██████╗ ███╗  ██╗███████╗██████╗
 ██╔════╝ ██║     ██╔═══██╗████╗ ██║██╔════╝██╔══██╗
 ██║      ██║     ██║   ██║██╔██╗██║█████╗  ██████╔╝
 ██║      ██║     ██║   ██║██║╚████║██╔══╝  ██╔══██╗
 ╚██████╗ ███████╗╚██████╔╝██║ ╚███║███████╗██║  ██║
  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚══╝╚══════╝╚═╝  ╚═╝
"""

STAGE_LABELS = {
    'ValidationStage':          ('🔍', 'Validando arquivo...'),
    'LoadingStage':             ('📂', 'Carregando HTML...'),
    'CleaningStage':            ('🧹', 'Limpando e aplicando semântica...'),
    'MaintenanceStage':         ('🏷️ ', 'Injetando comentários estruturais...'),
    'ExtractionStage':          ('📦', 'Extraindo CSS, imagens e scripts...'),
    'JavaScriptExtractionStage':('⚙️ ', 'Processando JavaScript...'),
    'OptimizationStage':        ('⚡', 'Otimizando CSS...'),
    'TailwindIntegrationStage': ('🎨', 'Integrando Tailwind...'),
    'OutputStage':              ('💾', 'Gerando arquivos de saída...'),
    'PostCssOptimizationStage': ('✨', 'Otimização final CSS...'),
    'SkillGeneratorStage':      ('🧠', 'Gerando skills/frontend.md...'),
}


class ClonerCLI:
    def __init__(self):
        self.uploader  = FileUploader()
        self.reporter  = Reporter()
        self.auth      = TokenAuth()
        self._check_rich()

    def _check_rich(self):
        if not RICH_AVAILABLE:
            print("[AVISO] Instale 'rich' para a interface visual completa: pip install rich")

    def _print_banner(self):
        if RICH_AVAILABLE:
            banner_text = Text(BANNER, style="bold cyan")
            console.print(banner_text)
            console.print(
                Panel.fit(
                    "[bold white]Process Cloner[/bold white] [dim]v1.0.3[/dim]  •  "
                    "[dim]Clone. Organize. Personalize.[/dim]",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
            console.print()
        else:
            print(BANNER)
            print("=" * 55)
            print("  Process Cloner v1.0 — Clone. Organize. Personalize.")
            print("=" * 55)

    def _print_tool_status(self):
        """Exibe tabela de ferramentas disponíveis."""
        import shutil
        tools = [
            ('LightningCSS', 'lightningcss', 'Otimização de CSS'),
            ('PurgeCSS',     'purgecss',     'Remoção de CSS não utilizado'),
            ('Prettier',     'prettier',     'Formatação de código'),
            ('Node.js',      'node',         'Runtime JavaScript'),
        ]

        if RICH_AVAILABLE:
            table = Table(title="Ferramentas Externas", border_style="dim", show_header=True, header_style="bold cyan")
            table.add_column("Ferramenta", style="bold")
            table.add_column("Status")
            table.add_column("Função", style="dim")

            for name, binary, desc in tools:
                available = shutil.which(binary) is not None
                status = "[green]✅ Disponível[/green]" if available else "[red]❌ Não encontrado[/red]"
                table.add_row(name, status, desc)

            console.print(table)
            console.print()
        else:
            print("\nFerramentas externas:")
            for name, binary, _ in tools:
                available = shutil.which(binary) is not None
                status = "✅" if available else "❌"
                print(f"  {status} {name}")
            print()

    def _get_input_file(self) -> Optional[str]:
        """Solicita o arquivo HTML ao usuário."""
        if RICH_AVAILABLE:
            console.rule("[cyan]Selecionar Arquivo[/cyan]")
            console.print()
            console.print("[bold]Arraste o arquivo HTML aqui ou cole o caminho completo:[/bold]")
            console.print("[dim](Arquivo gerado pelo SingleFile, HTTrack ou similar)[/dim]\n")
            raw = Prompt.ask("[cyan]>[/cyan]")
        else:
            print("\n--- Selecionar Arquivo ---")
            print("Arraste o arquivo HTML ou cole o caminho:")
            raw = input("> ")

        path = raw.strip().strip('"').strip("'")

        if not path:
            self._error("Nenhum arquivo informado.")
            return None

        resolved = self.uploader.resolve(path)
        if not resolved:
            self._error(f"Arquivo não encontrado: {path}")
            return None

        size_mb = os.path.getsize(resolved) / (1024 ** 2)
        if RICH_AVAILABLE:
            console.print(f"\n[green]✅ Arquivo detectado:[/green] {Path(resolved).name} [dim]({size_mb:.1f}MB)[/dim]\n")
        else:
            print(f"\n✅ Arquivo: {Path(resolved).name} ({size_mb:.1f}MB)\n")

        return resolved

    def _get_base_url(self) -> Optional[str]:
        """Pergunta pela base URL (opcional)."""
        if RICH_AVAILABLE:
            console.print("[dim]URL base do site original (opcional — ajuda a baixar imagens externas):[/dim]")
            url = Prompt.ask("[cyan]URL base[/cyan]", default="")
        else:
            print("URL base do site (opcional, pressione Enter para pular):")
            url = input("> ")

        return url.strip() or None

    def _get_output_dir(self) -> str:
        """Pergunta pelo diretório de saída."""
        default = "output"
        if RICH_AVAILABLE:
            out = Prompt.ask(f"[cyan]Pasta de saída[/cyan]", default=default)
        else:
            print(f"Pasta de saída [padrão: {default}]:")
            out = input("> ").strip() or default

        # Remove aspas e normaliza barras (Windows drag-and-drop)
        out = out.strip().strip('"').strip("'").replace('\\', '/').strip('/')
        return out or default

    def _confirm_start(self, file_path: str, base_url: Optional[str], out_dir: str) -> bool:
        """Confirma antes de iniciar o processamento."""
        if RICH_AVAILABLE:
            console.print()
            summary = Table(show_header=False, box=None, padding=(0, 1))
            summary.add_column(style="dim")
            summary.add_column(style="bold white")
            summary.add_row("Arquivo:",   Path(file_path).name)
            summary.add_row("Base URL:",  base_url or "[dim]não informado[/dim]")
            summary.add_row("Saída:",     out_dir)
            console.print(Panel(summary, title="[bold cyan]Resumo[/bold cyan]", border_style="cyan"))
            console.print()
            return Confirm.ask("[bold]Iniciar processamento?[/bold]", default=True)
        else:
            print(f"\nArquivo : {file_path}")
            print(f"Saída   : {out_dir}")
            ans = input("Iniciar? [S/n]: ").strip().lower()
            return ans in ('', 's', 'sim', 'y', 'yes')

    def _run_pipeline_with_progress(self, pipeline, context: dict) -> dict:
        """Executa o pipeline mostrando progresso em tempo real."""
        stages = pipeline.stages
        total  = len(stages)

        if RICH_AVAILABLE:
            console.print()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=35),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("[cyan]Processando...[/cyan]", total=total)

                for i, stage in enumerate(stages):
                    name = stage.__class__.__name__
                    emoji, label = STAGE_LABELS.get(name, ('🔄', name))
                    progress.update(task, description=f"{emoji} {label}", completed=i)
                    context = stage.process(context)

                progress.update(task, completed=total, description="[green]✅ Concluído!")
        else:
            for i, stage in enumerate(stages):
                name = stage.__class__.__name__
                _, label = STAGE_LABELS.get(name, ('', name))
                print(f"[{i+1}/{total}] {label}")
                context = stage.process(context)

        return context

    def _error(self, msg: str):
        if RICH_AVAILABLE:
            console.print(f"\n[bold red]❌ Erro:[/bold red] {msg}\n")
        else:
            print(f"\n❌ Erro: {msg}\n")

    def _print_success(self, result: dict):
        """Exibe relatório final após processamento bem-sucedido."""
        out = result.get('output', {})
        stats = self.reporter.summary(result)
        skill = result.get('skill_file')

        if RICH_AVAILABLE:
            console.print()
            console.rule("[green]Processamento Concluído[/green]")
            console.print()

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="dim", width=20)
            table.add_column(style="bold white")

            table.add_row("📄 HTML Original:", out.get('html_file', '—'))
            table.add_row("🎨 CSS Original:",  f"{out.get('css_file', '—')} [dim]({stats.get('css_size', '—')})[/dim]")
            
            # Destaque para o Shadow Build
            if 'shadow_css_size' in stats:
                table.add_row("⚡ CSS Otimizado:", f"{stats.get('shadow_css_size')} [bold green](-{stats.get('reduction')})[/bold green]")
                table.add_row("🧪 Tester Env:",   f"[bold cyan]{stats.get('tester_file', '—')}[/bold cyan]")

            if out.get('js_bundle'):
                table.add_row("⚙️  JS Bundle:", out['js_bundle'])
            table.add_row("🖼️  Imagens:", out.get('images_dir', '—'))
            
            skill_files = result.get('skill_files', [])
            if skill_files:
                for sf in skill_files:
                    table.add_row("🧠 " + os.path.basename(sf) + ":", sf)
            elif skill:
                table.add_row("🧠 Skill LLM:", skill)
            
            table.add_row("📋 Log:", "logs/processor.log")

            console.print(Panel(table, title="[bold green]Relatório de Performance[/bold green]", border_style="green"))
            console.print()
            console.print("[bold green]✅ Sucesso![/bold green] O CSS foi reduzido drasticamente na versão [bold]styles.safe.css[/bold].")
            console.print("[dim]Próximo passo:[/dim] Abra o [bold]tester.html[/bold] para validar o layout otimizado.")
            console.print("[dim]Dica:[/dim] Se estiver OK, você pode substituir o index.html pelo tester.html.\n")
        else:
            print("\n✅ Concluído!")
            print(f"  HTML    : {out.get('html_file')}")
            print(f"  CSS     : {out.get('css_file')} ({stats.get('css_size')})")
            if 'shadow_css_size' in stats:
                print(f"  SHADOW  : {stats.get('shadow_css_size')} (-{stats.get('reduction')})")
                print(f"  TESTER  : {stats.get('tester_file')}")
            print(f"  Imagens : {out.get('images_dir')}")
            if skill:
                print(f"  Skill   : {skill}")

    def _print_user_info(self, user_data: dict):
        """Exibe boas-vindas ao usuário autenticado."""
        plan  = user_data.get('plan', 'basic')
        email = user_data.get('email', '')
        if RICH_AVAILABLE:
            console.print(
                f"[dim]  Olá,[/dim] [bold]{email}[/bold]  "
                f"[dim]Plano:[/dim] [cyan]{plan.upper()}[/cyan]\n"
            )
        else:
            print(f"  Autenticado: {email} | Plano: {plan}\n")

    def run(self):
        """Loop principal da CLI."""
        self._print_banner()

        # 0. Autenticação — bloqueia sem token válido
        try:
            user_data = self.auth.ensure_authenticated()
            self._print_user_info(user_data)
        except AuthError as e:
            self._error(str(e))
            sys.exit(1)

        self._print_tool_status()

        # 1. Selecionar arquivo
        input_file = self._get_input_file()
        if not input_file:
            sys.exit(1)

        # 2. Base URL (opcional)
        base_url = self._get_base_url()

        # 3. Diretório de saída
        out_dir = self._get_output_dir()

        # 4. Confirmar
        if not self._confirm_start(input_file, base_url, out_dir):
            if RICH_AVAILABLE:
                console.print("\n[yellow]Operação cancelada.[/yellow]\n")
            else:
                print("\nCancelado.\n")
            sys.exit(0)

        # 5. Importar e montar pipeline
        from core.pipeline import build_pipeline
        from core.config import update_output_dir
        update_output_dir(out_dir)

        pipeline = build_pipeline()

        # 6. Executar com progresso
        try:
            result = self._run_pipeline_with_progress(pipeline, {
                'input_file': input_file,
                'base_url':   base_url,
            })
        except Exception as e:
            self._error(str(e))
            if RICH_AVAILABLE:
                console.print("[dim]Verifique logs/processor.log para detalhes.[/dim]\n")
            sys.exit(1)

        # 7. Relatório final
        self._print_success(result)

        # 8. Oferecer integração com Claude Code
        self._offer_claude_code(out_dir)

    def _offer_claude_code(self, out_dir: str):
        """Oferece abrir Claude Code na pasta gerada."""
        import shutil
        if not shutil.which('claude'):
            return

        if RICH_AVAILABLE:
            if Confirm.ask("\n[cyan]Abrir Claude Code na pasta gerada?[/cyan]", default=False):
                os.system(f'claude "{os.path.abspath(out_dir)}"')
        else:
            ans = input("\nAbrir Claude Code na pasta? [s/N]: ").strip().lower()
            if ans in ('s', 'sim', 'y'):
                os.system(f'claude "{os.path.abspath(out_dir)}"')
