import sys
import os

# Adiciona o caminho do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.stages.dataclear import run_dataclear_job
from agentic_api.schemas import Archetype
import json

def test_archetype(archetype):
    print(f"\n--- TESTANDO ARQUÉTIPO: {archetype} ---")
    
    # HTML Simulado - Mais longo para passar no Fidelity Scorer (BLOG)
    if archetype == Archetype.HUB:
        html = """
        <html>
            <head><title>Página de Hub</title></head>
            <body>
                <div class="card">
                    <a href="/noticia-1" class="title">Título da Notícia 1</a>
                    <p class="description">Esta é a descrição rica da notícia 1 que deve passar nos filtros de tamanho mínimo.</p>
                </div>
                <div class="card">
                    <a href="/noticia-2"><h2>Título da Notícia 2</h2></a>
                    <span class="summary">Resumo da notícia 2 para o dataset. Este resumo também é longo o suficiente.</span>
                </div>
                <div class="footer">
                    <a href="/privacidade">Política de Privacidade</a>
                </div>
            </body>
        </html>
        """
    else:
        html = """
        <html>
            <head><title>Artigo de Blog</title></head>
            <body>
                <article>
                    <h1>Título do Grande Artigo de Inteligência Artificial</h1>
                    <p>Este é o primeiro parágrafo substancial do artigo. A inteligência artificial está transformando o mundo de forma acelerada. É necessário compreender os impactos éticos e sociais desta tecnologia que é onipresente hoje.</p>
                    <p>O segundo parágrafo continua a explicação técnica sobre a NeuralSafety, uma empresa líder em proteção e auditoria de modelos de linguagem. Nós garantimos que o seu sistema seja seguro e confiável para os usuários finais.</p>
                    <p>Além disso, o terceiro parágrafo aborda a conformidade com as leis de proteção de dados, o que é fundamental para qualquer empresa moderna que opera no ambiente digital de hoje em dia.</p>
                </article>
                <nav>Links de navegação que devem ser ignorados.</nav>
            </body>
        </html>
        """

    config = {"archetype": archetype, "base_url": "https://exame.com", "fidelity_threshold": 0.4}
    
    try:
        result = run_dataclear_job(
            html_content=html,
            url="https://exame.com/test",
            executor_level="L0-test",
            config=config,
            capture_id="test-123",
            mission_id="mission-456"
        )
        
        print(f"Sucesso! Status: {result.get('waf_blocked')}")
        entries = result.get('dataset_entries', [])
        print(f"Entradas encontradas: {len(entries)}")
        
        if entries:
            data = entries[0]['data']
            if archetype == Archetype.HUB:
                items = data.get('hub_items', [])
                print(f"Hub Items: {len(items)}")
                for item in items:
                    print(f"  - {item['title']} | Snippet: {item['snippet']}")
            else:
                print(f"Título: {data.get('title')}")
                print(f"Markdown Body (primeiros 100 chars): {data.get('markdown_body', '')[:100]}...")

    except Exception as e:
        print(f"ERRO CRÍTICO NO TESTE: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_archetype(Archetype.BLOG)
    test_archetype(Archetype.HUB)
