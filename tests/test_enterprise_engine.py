import sys
import os
# Adiciona a raiz do projeto ao path para localizar o 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
from bs4 import BeautifulSoup

from core.stages.dataclear import DataClearStage

def test_enterprise_logic():
    print("[TESTE DE FOGO] Iniciando Auditoria Isolada da Engenharia v3")
    
    # HTML real simulado - TEXTO LONGO PARA PASSAR NO FILTRO
    mock_html = """
    <html>
        <body>
            <article class="post-content">
                <h1>Titulo Real: O Guia Definitivo de Machine Learning</h1>
                <div class="entry-content">
                    <p>O Machine Learning e uma subarea da Inteligencia Artificial que se concentra no desenvolvimento de algoritmos que permitem aos computadores aprender a partir de dados. Em vez de serem explicitamente programados para realizar uma tarefa, os computadores usam padroes nos dados para fazer previsoes ou tomar decisoes. Este processo e fundamental para a criacao de sistemas inteligentes que podem evoluir com o tempo.</p>
                    <p>Existem diversos tipos de aprendizado de maquina, incluindo o aprendizado supervisionado, o nao supervisionado e o aprendizado por reforcamento. No aprendizado supervisionado, o modelo e treinado em um conjunto de dados rotulados, o que significa que cada exemplo de treinamento e acompanhado pelo resultado correto. Isso permite que o algoritmo aprenda a mapear entradas para saidas de forma precisa e confiavel.</p>
                    <p>A limpeza de dados e um dos passos mais importantes em qualquer projeto de ciencia de dados. Sem dados limpos, ate o algoritmo mais avancado produzira resultados de baixa qualidade. Portanto, investir tempo na preparacao e no refino dos dados e essencial para garantir que as previsoes do modelo sejam uteis e acionaveis para o negocio.</p>
                </div>
                <div class="related-posts">
                    <h3>Relacionado</h3>
                </div>
            </article>
        </body>
    </html>
    """
    
    config = {
        "archetype": "blog",
        "fidelity_threshold": 0.3,
        "allowed_domains": "blog.dsacademy.com.br"
    }
    
    stage = DataClearStage(config=config)
    soup = BeautifulSoup(mock_html, 'lxml')
    context = {
        "url": "https://blog.dsacademy.com.br/guia-ml",
        "soup": soup,
        "executor_level": "unit-test"
    }
    
    # Reduzimos o chunk_size para forçar a quebra no teste
    result = stage.process(context)
    entries = result.get('dataset_entries', [])
    
    if not entries:
        print("ERRO: Dataset vazio!")
        return

    entry = entries[0]
    data = entry['data']
    
    print("\n--- RESULTADOS DA AUDITORIA ---")
    print(f"TITULO CAPTURADO: {data['title']}")
    print(f"FIDELITY SCORE: {entry['fidelity_score']}")
    
    print("\n--- ANALISE DE CHUNKS ---")
    # Forçamos a quebra de chunks curtos para testar a fronteira
    chunks = stage._create_chunks(data['markdown_body'], chunk_size=200, overlap=20)
    
    for i, chunk in enumerate(chunks):
        text = chunk['text']
        last_char = text[-1]
        print(f"Chunk {i} (Tamanho {len(text)}): '{text[:60]}...' [Fim: '{last_char}']")
        
        if last_char not in ['.', '!', '?', ':', '\n']:
            print(f"AVISO: Chunk {i} cortado sem pontuacao!")
        else:
            print(f"SUCESSO: Chunk {i} respeitou a sentenca.")

if __name__ == "__main__":
    test_enterprise_logic()
