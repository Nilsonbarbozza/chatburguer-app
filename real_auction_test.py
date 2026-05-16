import asyncio
import json
import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path para importar os módulos core
sys.path.append(str(Path(__file__).parent))

from concurrent.futures import ProcessPoolExecutor
from core.executors.waterfall import WaterfallExtractor

async def run_multi_page_test():
    base_url = "https://www.megaleiloes.com.br/imoveis"
    all_extracted_items = []
    
    print(f"\n--- OPERACAO RADAR: SCAN MULTI-PAGINA (1-5) ---")
    
    # Pool de processos para o DataClear
    process_pool = ProcessPoolExecutor(max_workers=4)
    extractor = WaterfallExtractor(process_pool)
    
    try:
        for page in range(1, 6):
            url = f"{base_url}?pagina={page}" if page > 1 else base_url
            print(f"[{page}/5] Escaneando Alvo: {url}...")
            
            try:
                result = await extractor.extract(
                    url=url,
                    render_js=True, 
                    force_stealth=True,
                    archetype="auction_grid",
                    fidelity_threshold=0.2,
                    capture_id=f"ENGINEER-SCAN-P{page}"
                )
                
                items = result.get("hub_items", [])
                all_extracted_items.extend(items)
                print(f"      -> Sucesso: {len(items)} itens encontrados.")
                
            except Exception as e:
                print(f"      -> Erro na pagina {page}: {e}")
            
            # Pequeno delay para evitar bloqueio agressivo
            await asyncio.sleep(2)
            
        # Consolidação Final
        debug_output = {
            "total_pages": 10,
            "total_items_count": len(all_extracted_items),
            "executor": "L34-playwright",
            "all_items": all_extracted_items
        }
        
        output_path = "auction_result_debug.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(debug_output, f, indent=2, ensure_ascii=False)
            
        print(f"\n[OK] SCAN COMPLETO CONCLUIDO")
        print(f"📂 ARQUIVO FINAL: {os.path.abspath(output_path)}")
        print(f"📦 TOTAL DE ITENS ESTRUTURADOS: {len(all_extracted_items)}")
        
    except Exception as e:
        print(f"\n[FAIL] FALHA CRITICA NO SCAN: {str(e)}")
    finally:
        process_pool.shutdown()

if __name__ == "__main__":
    asyncio.run(run_multi_page_test())
