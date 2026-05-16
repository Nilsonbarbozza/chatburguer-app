import asyncio
import json
import logging
from core.executors.waterfall import WaterfallExtractor
from agentic_api.schemas import Archetype

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('regression_test')

async def test_blog_regression():
    # Alvo: Artigo específico da Exame
    url = "https://exame.com/inteligencia-artificial/10-momentos-historicos-que-marcaram-a-evolucao-da-inteligencia-artificial/"
    
    print(f"\n--- TESTE DE NAO-REGRESSAO: ARQUETIPO ARTICLE ---")
    print(f"Alvo: {url}\n")
    
    from concurrent.futures import ProcessPoolExecutor
    pool = ProcessPoolExecutor(max_workers=1)
    extractor = WaterfallExtractor(process_pool=pool)
    
    try:
        # Chamada correta: url, render_js, force_stealth, archetype, fidelity_threshold
        result = await extractor.extract(
            url=url, 
            render_js=True, 
            force_stealth=False, 
            archetype="article", 
            fidelity_threshold=0.1
        )
        
        print(f"\n[RESULTADO JSON SALVO EM blog_result_debug.json]")
        with open("blog_result_debug.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        markdown_body = result.get("markdown_body", "")
        if markdown_body:
            # Validação crítica
            if len(markdown_body) > 500:
                print(f"\n[PASS] Extracao de artigo continua integra.")
            else:
                print(f"\n[FAIL] Conteudo insuficiente.")
        else:
            print(f"\n[FAIL] Markdown body vazio.")
            
    except Exception as e:
        print(f"\n[ERRO CRITICO] {e}")

if __name__ == "__main__":
    asyncio.run(test_blog_regression())
