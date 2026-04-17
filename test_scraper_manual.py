import os
import sys
from pathlib import Path

# Adiciona o dretório raiz ao PATH para as importações funcionarem
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import Pipeline
from core.config import update_output_dir

# Importamos TODAS as etapas do pipeline (menos a de validação de token para este teste)
from core.stages.scraper import ScraperStage
from core.stages.loading import LoadingStage
from core.stages.cleaning import CleaningStage
from core.stages.maintenance import MaintenanceStage
from core.stages.extraction import ExtractionStage
from core.stages.javascript import JavaScriptExtractionStage
from core.stages.refactoring import RefactoringStage
from core.stages.optimization import OptimizationStage
from core.stages.output import OutputStage
from core.skill_generator import SkillGeneratorStage

def run_full_manual_test():
    # URL alvo para o teste
    url = "https://betterproposals.io/product/creating-proposals"
    output_dir = "betterpropost_test"
    
    print(f"🚀 INICIANDO TESTE DE PIPELINE COMPLETO (VIA URL - BYPASS TOKEN)")
    print(f"🔗 Alvo: {url}")
    print(f"📁 Pasta de Saída: {output_dir}")
    print("-" * 75)

    # Configura o diretório de saída para este teste
    update_output_dir(output_dir)

    # Montamos o pipeline completo (Stage 0 ao Stage 12)
    pipeline = (
        Pipeline()
        .add_stage(ScraperStage())             # Etapa 0: Coleta Inteligente (Playwright)
        .add_stage(LoadingStage())             # Etapa 2: BeautifulSoup
        .add_stage(CleaningStage())            # Etapa 3: Limpeza de Lixo
        .add_stage(MaintenanceStage())         # Etapa 4: Comentários de Manutenção
        .add_stage(ExtractionStage())          # Etapa 5: Extração de Ativos (CSS/Imagens reais)
        .add_stage(JavaScriptExtractionStage()) # Etapa 6: Coleta de Scripts
        .add_stage(RefactoringStage())         # Etapa 6.5: Refatoração Semântica + Design System
        .add_stage(OptimizationStage())        # Etapa 7: Otimização
        .add_stage(OutputStage())              # Etapa 9: Geração de Saída (index.html + styles.css)
        .add_stage(SkillGeneratorStage())      # Etapa 12: Geração de Memória para IA (Skills)
    )

    context = {
        'url': url,
        'input_file': None,
        'output_dir': output_dir
    }

    try:
        result = pipeline.execute(context)
        print("-" * 75)
        print(f"✅ PIPELINE COMPLETO EXECUTADO COM SUCESSO!")
        print(f"📄 HTML Final: {result['output']['html_file']}")
        print(f"🎨 CSS Final:  {result['output']['css_file']}")
        print(f"🧠 Skill gerada: {result.get('skill_file')}")
        print(f"\n💡 AGORA SIM: O site foi baixado via URL com fidelidade total e estrutura completa!")
    except Exception as e:
        print(f"❌ FALHA NO PIPELINE: {e}")

if __name__ == "__main__":
    run_full_manual_test()
