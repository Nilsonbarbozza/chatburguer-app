import asyncio
import logging
import json
from core.stages.dataclear import run_dataclear_job
from core.executors.executor_l0_aiohttp import GOOGLEBOT_HEADERS as L0_HEADERS
from agentic_api.routes import GOOGLEBOT_HEADERS as API_HEADERS
from core.stages.advanced_miner import extract_json_ld, extract_article_from_json_ld

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verify-OS014")

def test_headers():
    logger.info("🧪 Testando Sítio Alpha: Headers do Googlebot...")
    assert "Googlebot" in L0_HEADERS["User-Agent"]
    assert "Googlebot" in API_HEADERS["User-Agent"]
    logger.info("✅ Headers validados.")

def test_dataclear_autopsy():
    logger.info("🧪 Testando Sítio Bravo: Autópsia de Dados (JSON-LD)...")
    
    mock_html = f"""
    <html>
        <head>
            <script type="application/ld+json">
            {{
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": "Título Secreto via SEO",
                "articleBody": "{"Este é o conteúdo real extraído via JSON-LD que o SPA esconderia. " * 20}"
            }}
            </script>
        </head>
        <body>
            <div id="root">Carregando...</div>
        </body>
    </html>
    """
    
    config = {"archetype": "blog", "fidelity_threshold": 0.1}
    result = run_dataclear_job(mock_html, "https://test.com", "L0", config)
    
    entries = result.get("dataset_entries", [])
    if not entries:
        logger.error("❌ Nenhuma entrada gerada no test_dataclear_autopsy")
    
    assert len(entries) > 0
    markdown = entries[0]["data"]["markdown_body"]
    
    logger.info(f"Conteúdo extraído: {markdown}")
    assert "Este é o conteúdo real extraído via JSON-LD" in markdown
    logger.info("✅ Autópsia de Dados (JSON-LD) validada.")

def test_next_data_autopsy():
    logger.info("🧪 Testando Sítio Bravo: Autópsia de Dados (Next.js)...")
    
    mock_html = f"""
    <html>
        <body>
            <script id="__NEXT_DATA__" type="application/json">
            {{
                "props": {{
                    "pageProps": {{
                        "article": {{
                            "content": "{"Conteúdo extraído do estado interno do Next.js. " * 20}"
                        }}
                    }}
                }}
            }}
            </script>
        </body>
    </html>
    """
    
    config = {"archetype": "blog", "fidelity_threshold": 0.1}
    result = run_dataclear_job(mock_html, "https://next-test.com", "L0", config)
    
    entries = result.get("dataset_entries", [])
    assert len(entries) > 0
    markdown = entries[0]["data"]["markdown_body"]
    
    logger.info(f"Conteúdo extraído: {markdown}")
    assert "Conteúdo extraído do estado interno do Next.js" in markdown
    logger.info("✅ Autópsia de Dados (Next.js) validada.")

def test_miner_standalone():
    logger.info("🧪 Testando Minerador Standalone...")
    mock_html = """<script type="application/ld+json">{"@type": "Article", "articleBody": "Texto de teste"}</script>"""
    blocks = extract_json_ld(mock_html)
    logger.info(f"Blocks found: {blocks}")
    assert len(blocks) == 1
    article = extract_article_from_json_ld(blocks)
    assert article is not None
    assert article["articleBody"] == "Texto de teste"
    logger.info("✅ Minerador Standalone validado.")

if __name__ == "__main__":
    try:
        test_miner_standalone()
        test_headers()
        test_dataclear_autopsy()
        test_next_data_autopsy()
        logger.info("\n🏆 TODOS OS TESTES LOCAIS DA OS-014 PASSARAM!")
    except Exception as e:
        logger.error(f"\n❌ FALHA NA VALIDAÇÃO: {e}")
        import traceback
        traceback.print_exc()
