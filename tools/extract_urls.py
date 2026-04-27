import json
import sys
import os

def extract(input_file, output_file):
    urls = set()
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    url = data.get('url')
                    if url:
                        urls.add(url)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in sorted(list(urls)):
                f.write(f'{url}\n')
        
        print(f'Done! {len(urls)} URLs únicas extraídas para {output_file}')
    except Exception as e:
        print(f'Erro: {e}')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Uso: python extract_urls.py <input.jsonl> <output.txt>')
    else:
        extract(sys.argv[1], sys.argv[2])
