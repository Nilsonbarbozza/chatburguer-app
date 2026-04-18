"""
core/pipeline.py
Montagem do pipeline — importa todos os stages e constrói a sequência
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

logger = logging.getLogger('html_processor')


class ProcessorStage(ABC):
    @abstractmethod
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class Pipeline:
    def __init__(self):
        self.stages: List[ProcessorStage] = []

    def add_stage(self, stage: ProcessorStage) -> 'Pipeline':
        self.stages.append(stage)
        return self

    def execute(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        context = initial_context
        for stage in self.stages:
            try:
                context = stage.process(context)
            except Exception as e:
                logger.error(f"❌ Erro no estágio {stage.__class__.__name__}: {e}")
                raise
        return context


def build_pipeline(mode: str = 'web', redact_pii: bool = True) -> Pipeline:
    """
    Monta o pipeline dinamicamente com base no modo de operação.
    Monta o pipeline completo v1.0.

    Ordem das etapas:
      1.  Validation       → falha rápida antes de qualquer I/O
      2.  Loading          → soup disponível para todos os stages
      3.  Cleaning         → semântica e head limpos
      4.  Maintenance      → comentários estruturais
      5.  Extraction       → CSS / imagens / scripts externos
      6.  JS Extraction    → scripts inline → main.js
      7.  Optimization     → CSS otimizado
      8.  Tailwind         → CDN opcional (via USE_TAILWIND=true)
      9.  Output           → gera index.html + styles.css
      10. PostCSS          → PurgeCSS + LightningCSS final
      11. SkillGenerator   → gera skills/frontend.md para LLMs
    """
    from core.stages.scraper      import ScraperStage
    from core.stages.validation   import ValidationStage
    from core.stages.loading      import LoadingStage
    from core.stages.cleaning     import CleaningStage
    from core.stages.maintenance  import MaintenanceStage
    from core.stages.extraction   import ExtractionStage
    from core.stages.javascript   import JavaScriptExtractionStage
    from core.stages.optimization import OptimizationStage, PostCssOptimizationStage
    from core.stages.shadow_validation import ShadowValidationStage
    from core.stages.tailwind     import TailwindIntegrationStage
    from core.stages.refactoring  import RefactoringStage
    from core.stages.output       import OutputStage
    from core.skill_generator     import SkillGeneratorStage
    from core.stages.dataclear    import DataClearStage

    pipeline = Pipeline()
    
    # Estágios Comuns
    pipeline.add_stage(ScraperStage())
    pipeline.add_stage(ValidationStage())
    pipeline.add_stage(LoadingStage())
    pipeline.add_stage(CleaningStage())
    
    if mode == 'web':
        # Pipeline Completo para Web
        pipeline.add_stage(MaintenanceStage())
        pipeline.add_stage(ExtractionStage())
        pipeline.add_stage(JavaScriptExtractionStage())
        pipeline.add_stage(RefactoringStage())
        pipeline.add_stage(OptimizationStage())
        pipeline.add_stage(TailwindIntegrationStage())
        pipeline.add_stage(OutputStage())
        pipeline.add_stage(PostCssOptimizationStage())
        pipeline.add_stage(ShadowValidationStage())
        pipeline.add_stage(SkillGeneratorStage())
    
    elif mode == 'dataset':
        # Pipeline Otimizado para Dataset de IA
        pipeline.add_stage(DataClearStage(redact_pii=redact_pii))
        pipeline.add_stage(OutputStage())

    return pipeline
