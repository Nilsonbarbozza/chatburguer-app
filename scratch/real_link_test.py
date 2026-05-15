import sys
import os
import requests

# Adiciona o caminho do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.stages.dataclear import run_dataclear_job
from agentic_api.schemas import Archetype
import json

def test_real_links():
    links = [
        {"url": "https://exame.com/inteligencia-artificial/", "archetype": Archetype.HUB},
        {"url": "https://exame.com/inteligencia-artificial/ao-vivo-no-youtube-robo-mostra-como-pode-substituir-20-milhoes-de-empregos-agora-mesmo/", "archetype": Archetype.BLOG}
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for link in links:
        url = link["url"]
        archetype = link["archetype"]
        print(f"\n--- TESTANDO LINK REAL ({archetype}): {url} ---")
        
        try:
            print(f"Baixando HTML...")
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text
            print(f"HTML baixado ({len(html)} chars). Status: {response.status_code}")
            
            config = {"archetype": archetype, "base_url": "https://exame.com", "fidelity_threshold": 0.3}
            
            result = run_dataclear_job(
                html_content=html,
                url=url,
                executor_level="L0-real-test",
                config=config
            )
            
            entries = result.get('dataset_entries', [])
            print(f"Sucesso! Entradas: {len(entries)}")
            
            if entries:
                data = entries[0]['data']
                if archetype == Archetype.HUB:
                    items = data.get('hub_items', [])
                    print(f"Hub Items encontrados: {len(items)}")
                    # Mostra os 3 primeiros para validar refino
                    for item in items[:3]:
                        print(f"  - {item['title'][:50]}... | Snippet: {item['snippet'][:80]}...")
                else:
                    print(f"Título extraído: {data.get('title')}")
                    print(f"Markdown Body (primeiros 200 chars):\n{data.get('markdown_body', '')[:200]}...")
            else:
                print("AVISO: Nenhuma entrada gerada (possível bloqueio WAF ou falha na extração densa local).")

        except Exception as e:
            print(f"FALHA NO TESTE REAL: {str(e)}")

if __name__ == "__main__":
    test_real_links()
