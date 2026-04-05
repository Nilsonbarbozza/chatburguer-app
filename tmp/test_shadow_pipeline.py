
import os
import sys
from pathlib import Path

# Adiciona o diretório atual ao path para importar core
sys.path.append(os.getcwd())

from core.pipeline import build_pipeline
from core.config import update_output_dir, get_paths

def test_shadow_build():
    test_file = 'test_input.html'
    out_dir = 'test_output'
    
    # Cria um HTML de teste com CSS inline e classes do "Tailwind"
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Shadow Build</title>
        <style>
            .tw-bg-blue-500 { background-color: blue; }
            .tw-p-4 { padding: 1rem; }
            .unused-class { color: red; }
            .inline_123 { border: 1px solid black; }
        </style>
    </head>
    <body class="tw-bg-blue-500 tw-p-4">
        <h1 class="inline_123">Hello World</h1>
        <div data-state="open">Menu Aberto</div>
    </body>
    </html>
    """
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"--- Iniciando Teste de Shadow Build ---")
    update_output_dir(out_dir)
    pipeline = build_pipeline()
    
    context = {
        'input_file': test_file,
        'base_url': None
    }
    
    try:
        pipeline.execute(context)
        
        paths = get_paths()
        print(f"\nVerificando arquivos em {out_dir}:")
        
        files_to_check = [
            ('index.html', os.path.join(out_dir, 'index.html')),
            ('styles.css', paths['STYLE_FILE']),
            ('styles.safe.css', paths['SAFE_STYLE_FILE']),
            ('tester.html', paths['TESTER_FILE'])
        ]
        
        all_ok = True
        for name, path in files_to_check:
            exists = os.path.exists(path)
            status = "✅" if exists else "❌"
            size = os.path.getsize(path) if exists else 0
            print(f"  {status} {name:15}: {path} ({size} bytes)")
            if not exists: all_ok = False
            
        if all_ok:
            # Verifica se o tester.html aponta para o CSS seguro
            with open(paths['TESTER_FILE'], 'r', encoding='utf-8') as f:
                content = f.read()
                if 'styles.safe.css' in content and 'AMBIENTE DE SOMBRA' in content:
                    print("  ✅ tester.html validado (link e banner OK)")
                else:
                    print("  ❌ tester.html falhou na validação de conteúdo")
                    all_ok = False
            
            # Verifica se o styles.safe.css não contém a classe não utilizada
            with open(paths['SAFE_STYLE_FILE'], 'r', encoding='utf-8') as f:
                css = f.read()
                if 'unused-class' not in css:
                    print("  ✅ Otimização CSS validada (unused-class removida)")
                else:
                    print("  ❌ Otimização CSS falhou (unused-class ainda presente)")
                    all_ok = False
                    
        if all_ok:
            print("\n🎉 TESTE BEM SUCEDIDO!")
        else:
            print("\n🛑 TESTE FALHOU!")
            
    finally:
        # Cleanup
        # if os.path.exists(test_file): os.remove(test_file)
        pass

if __name__ == "__main__":
    test_shadow_build()
