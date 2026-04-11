import sys
import os
from pathlib import Path

# Adiciona o diretório atual ao path para importar o core
sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import build_pipeline
from core.config   import update_output_dir

def run_test(file_path):
    print(r"""
  ____  _               _                 _____         _   
 / ___|| |__   __ _  __| | _____      __ |_   _|__  ___| |_ 
 \___ \| '_ \ / _` |/ _` |/ _ \ \ /\ / /   | |/ _ \/ __| __|
  ___) | | | | (_| | (_| | (_) \ V  V /    | |  __/\__ \ |_ 
 |____/|_| |_|\__,_|\__,_|\___/ \_/\_/     |_|\___||___/\__|
    """)
    print(f"START: Iniciando Teste Shadow Build para: {file_path}")
    
    # Define a pasta de saída como 'output_test'
    # Isso evita que você sobrescreva seus arquivos de produção
    update_output_dir('output_test')
    
    # Constrói o pipeline (inclui ShadowValidationStage + Novo Extrator de SVG)
    pipeline = build_pipeline()
    
    try:
        # Prepara o contexto inicial
        initial_context = {
            'input_file': file_path, 
            'base_url': 'https://prismlive.com/en-us/studio/'
        }
        
        # Executa o pipeline completo v1.0
        result = pipeline.execute(initial_context)
        
        print("\n" + "="*60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print(f"📂 Pasta de saída: {os.path.abspath('output_test')}")
        print(f"🌐 Versão Final:   output_test/index.html")
        print(f"🧪 Versão Shadow:  output_test/tester.html (com styles.safe.css)")
        print("\nPRÓXIMOS PASSOS:")
        print("1. Abra o 'tester.html' no navegador.")
        print("2. Verifique se o banner azul aparece no topo.")
        print("3. Confira os logs acima para mensagens do 'Shadow Health Check'.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERRO DURANTE O TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Caminho do arquivo alvo
    # Ajustado conforme sua tentativa anterior
    target = r"C:\Users\Ti\Downloads\efect.html"
    
    if not os.path.exists(target):
        print(f"❌ Arquivo não encontrado: {target}")
        print("Edite o arquivo 'test_shadow.py' e ajuste a variável 'target'.")
    else:
        run_test(target)
