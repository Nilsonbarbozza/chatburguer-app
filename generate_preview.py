import json
import os

def generate_preview(jsonl_path: str, output_md: str, num_samples: int = 5):
    """
    Gera um preview Markdown legível a partir de um arquivo JSONL.
    """
    if not os.path.exists(jsonl_path):
        print(f"Erro: Arquivo {jsonl_path} não encontrado.")
        return

    with open(jsonl_path, 'r', encoding='utf-8') as f, open(output_md, 'w', encoding='utf-8') as out:
        out.write(f"# 💎 Diamond Elite Preview: Missão DS Academy\n\n")
        out.write(f"Este arquivo é uma visão parseada do dataset JSONL para auditoria humana.\n\n")
        out.write(f"---\n\n")
        
        for i, line in enumerate(f):
            if i >= num_samples:
                break
            
            data = json.loads(line)
            content = data['data']
            
            out.write(f"## Amostra {i+1}: {content.get('title', 'Sem Título')}\n")
            out.write(f"**URL Canônica:** {data.get('url')}\n")
            out.write(f"**Fidelity Score:** {data.get('fidelity_score')}\n")
            out.write(f"**Executor:** {data.get('executor')}\n\n")
            out.write(f"### Conteúdo (Markdown Body):\n\n")
            out.write(content.get('markdown_body', ''))
            out.write(f"\n\n---\n\n")
            
    print(f"✅ Preview gerado em: {output_md}")

if __name__ == "__main__":
    path = "data/curated/2026/04/30/230b495e-347d-4d9a-9b14-0d66fabe10d2/dataset.jsonl"
    output = "data/curated/2026/04/30/230b495e-347d-4d9a-9b14-0d66fabe10d2/preview_diamond.md"
    generate_preview(path, output)
