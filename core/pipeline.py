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


def build_pipeline() -> Pipeline:
    """
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
    from core.stages.validation   import ValidationStage
    from core.stages.loading      import LoadingStage
    from core.stages.cleaning     import CleaningStage
    from core.stages.maintenance  import MaintenanceStage
    from core.stages.extraction   import ExtractionStage
    from core.stages.javascript   import JavaScriptExtractionStage
    from core.stages.optimization import OptimizationStage, PostCssOptimizationStage
    from core.stages.shadow_validation import ShadowValidationStage
    from core.stages.tailwind     import TailwindIntegrationStage
    from core.stages.output       import OutputStage
    from core.skill_generator     import SkillGeneratorStage

    return (
        Pipeline()
        .add_stage(ValidationStage())
        .add_stage(LoadingStage())
        .add_stage(CleaningStage())
        .add_stage(MaintenanceStage())
        .add_stage(ExtractionStage())
        .add_stage(JavaScriptExtractionStage())
        .add_stage(OptimizationStage())
        .add_stage(TailwindIntegrationStage())
        .add_stage(OutputStage())
        .add_stage(PostCssOptimizationStage())
        .add_stage(ShadowValidationStage())
        .add_stage(SkillGeneratorStage())
    )
