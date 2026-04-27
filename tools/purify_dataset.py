import json
import re
import os

def purify():
    input_file = "data/output/ds_academy_articles_phase2_2026-04-27.jsonl"
    output_file = "data/output/ds_academy_articles_phase2_CLEAN.jsonl"
    
    print(f"--- Ajuste Fino de Fidelidade (Caca aos Ultimos Fragmentos) ---")
    
    clean_count = 0
    discard_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip(): continue
            data = json.loads(line)
            
            title = data['data'].get('title', '')
            body = data['data'].get('markdown_body', '')
            
            # FILTRO DE TITULO (Mantemos o bloqueio no titulo 'Compartilhe isso')
            if "Compartilhe isso" in title or len(title) < 5:
                discard_count += 1
                continue

            # SNIPER UNIVERSAL
            body = re.sub(r'\[Compartilhar|Share|Follow us.*?\]\(.*?\)', '', body, flags=re.DOTALL | re.IGNORECASE)
            body = re.sub(r'\(abre em nova janela|opens in new window\)', '', body, flags=re.IGNORECASE)
            body = re.sub(r'(?i)(Compartilhe|Share|Siga) (isso|this):.*?(?=###|##|#|\n\n|$)', '', body, flags=re.DOTALL)
            
            body = body.strip()
            
            # RATIO DE LINKS (Subimos para 0.85 para posts curtissimos com muitos links no rodape)
            link_count = len(re.findall(r'\[.*?\]\(.*?\)', body))
            word_count = len(body.split())
            
            if word_count > 0 and (link_count / word_count) > 0.85:
                discard_count += 1
                continue

            # MASSA MÍNIMA (150 chars - pilar de micro-conteudo)
            if len(body) < 150:
                discard_count += 1
                continue

            data['data']['markdown_body'] = body
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            clean_count += 1

    print(f"Purificacao Completa! {clean_count} artigos consolidados no Data Lake.")

if __name__ == '__main__':
    purify()
