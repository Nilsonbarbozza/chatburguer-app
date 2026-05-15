import sys
import os
import requests
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.stages.dataclear import run_dataclear_job
from agentic_api.schemas import Archetype

def test_real_links():
    links = [
        {"url": "https://exame.com/", "archetype": Archetype.HUB},
        {"url": "https://exame.com/inteligencia-artificial/", "archetype": Archetype.HUB},
        {"url": "https://exame.com/inteligencia-artificial/ao-vivo-no-youtube-robo-mostra-como-pode-substituir-20-milhoes-de-empregos-agora-mesmo/", "archetype": Archetype.BLOG},
        {"url": "https://olhardigital.com.br/", "archetype": Archetype.HUB},
        {"url": "https://olhardigital.com.br/noticias/", "archetype": Archetype.HUB},
        {"url": "https://olhardigital.com.br/2024/02/09/ciencia-e-espaco/entenda-como-funciona-o-novo-telescopio-james-webb/", "archetype": Archetype.BLOG}
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    results = []

    for link in links:
        url = link["url"]
        archetype = link["archetype"]
        print(f"\n--- TESTANDO LINK REAL ({archetype}): {url} ---")
        
        try:
            print(f"Baixando HTML...")
            t0_fetch = time.time()
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text
            print(f"HTML baixado ({len(html)} chars) em {time.time()-t0_fetch:.2f}s. Status: {response.status_code}")
            
            config = {"archetype": archetype, "base_url": url, "fidelity_threshold": 0.3}
            
            t0_process = time.time()
            result = run_dataclear_job(
                html_content=html,
                url=url,
                executor_level="L0-real-test",
                config=config
            )
            time_process = time.time() - t0_process
            print(f"Processamento concluído em {time_process:.2f}s")
            
            entries = result.get('dataset_entries', [])
            
            if entries:
                data = entries[0]['data']
                if archetype == Archetype.HUB:
                    items = data.get('hub_items', [])
                    print(f"Hub Items encontrados: {len(items)}")
                    sample = []
                    for item in items[:3]:
                        print(f"  - [{item.get('timestamp')}] {item['title'][:50]}... | Snippet: {item['snippet'][:80]}... | URL: {item['url'][:50]}")
                        sample.append(item)
                    results.append({"url": url, "type": "hub", "time_ms": int(time_process*1000), "items_count": len(items), "sample": sample})
                else:
                    md_body = data.get('markdown_body', '')
                    print(f"Título extraído: {data.get('title')}")
                    print(f"Markdown Body (primeiros 200 chars):\n{md_body[:200]}...")
                    # Check for links
                    import re
                    links_found = re.findall(r'\[.*?\]\(.*?\)', md_body)
                    print(f"Links encontrados no markdown: {len(links_found)}")
                    results.append({"url": url, "type": "blog", "time_ms": int(time_process*1000), "md_length": len(md_body), "links_found": len(links_found)})
            else:
                print("AVISO: Nenhuma entrada gerada.")

        except Exception as e:
            print(f"FALHA NO TESTE REAL: {str(e)}")

    print("\n\n--- RESUMO DE VALIDAÇÃO ---")
    with open("validation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Salvo em validation_results.json")

if __name__ == "__main__":
    test_real_links()
