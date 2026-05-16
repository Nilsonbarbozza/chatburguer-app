import pytest
from core.stages.dataclear import run_dataclear_job, ExtractionTimeout
from core.schemas.extraction import ExtractionMethod, DataClearResult
import time

def test_run_dataclear_job_contracts():
    """Verifica se run_dataclear_job retorna o contrato DataClearResult."""
    # Texto em português com life signals para passar no fidelity_score > 0.6
    paragrafo1 = "Este é um artigo completo onde explicamos como o sistema funciona para os usuários que buscam qualidade. São muitos detalhes técnicos mas o resultado é excelente ou superior ao esperado por todos."
    paragrafo2 = "O Batalhão trabalha com afinco para garantir que nenhum dado seja perdido onde a extração ocorre de forma fluida. Este processo é complexo mas necessário para a NeuralSafety ou qualquer empresa de IA."
    texto_longo = f"{paragrafo1}\n\n{paragrafo2}"
    
    html = f"<html><body><article><h1>Título do Post</h1><p>{texto_longo}</p></article></body></html>"
    url = "https://example.com"
    config = {"archetype": "blog"}
    
    result = run_dataclear_job(html, url, "L0", config)
    
    assert isinstance(result, DataClearResult)
    assert result.extraction_method != ExtractionMethod.FAILED
    assert result.quality_score > 0

def test_strategy_isolation_failure():
    """Verifica se uma falha em uma estratégia não derruba o job."""
    # HTML que causaria erro em algum extrator se não houvesse isolamento
    html = "<html><body>MALFORMED</body></html>"
    url = "https://example.com"
    config = {"archetype": "blog"}
    
    # Se fallbacks funcionarem, ele deve chegar na Tática 3 (DOM) e retornar algo (mesmo que vazio)
    result = run_dataclear_job(html, url, "L0", config)
    assert isinstance(result, DataClearResult)

def test_quality_scorer_signals():
    """Verifica se o quality scorer bloqueia conteúdos irrelevantes."""
    from core.stages.dataclear import _semantic_quality_score
    
    # Caso 1: Conteúdo curto demais
    assert _semantic_quality_score("curto") == 0.0
    
    # Caso 2: Navegação pura (link density alta)
    nav_text = "https://link1.com https://link2.com https://link3.com https://link4.com"
    assert _semantic_quality_score(nav_text) < 0.35
    
    # Caso 3: Conteúdo real
    real_text = "Este é um parágrafo longo com informações úteis sobre o sistema de extração.\n\n" * 5
    assert _semantic_quality_score(real_text) >= 0.35

def test_singleton_behavior():
    """Verifica se o singleton não reinstancia o cleaner desnecessariamente."""
    from core.stages.dataclear import _get_or_create_cleaner
    config = {"archetype": "blog"}
    
    c1 = _get_or_create_cleaner(config)
    c2 = _get_or_create_cleaner(config)
    
    assert c1 is c2

@pytest.mark.skipif(not hasattr(time, 'alarm'), reason="SIGALRM not supported on this OS")
def test_extraction_timeout():
    """Verifica se o timeout interrompe jobs longos (apenas Linux)."""
    from core.stages.dataclear import extraction_timeout
    
    with pytest.raises(ExtractionTimeout):
        with extraction_timeout(seconds=1):
            time.sleep(2)
