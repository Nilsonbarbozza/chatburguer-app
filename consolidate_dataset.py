
import os
import glob
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ConsolidadorGold")

def consolidate_mission(mission_path: str):
    """
    Une todos os fragmentos capture_*.jsonl em um único dataset.jsonl.
    """
    logger.info(f"🔍 Iniciando consolidação em: {mission_path}")
    
    pattern = os.path.join(mission_path, "capture_*.jsonl")
    fragments = glob.glob(pattern)
    
    if not fragments:
        logger.warning("⚠️ Nenhum fragmento encontrado para consolidar.")
        return

    output_file = os.path.join(mission_path, "dataset.jsonl")
    
    count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for frag in sorted(fragments):
            with open(frag, 'r', encoding='utf-8') as infile:
                content = infile.read()
                outfile.write(content)
                count += 1
                
    logger.info(f"✅ SUCESSO! {count} fragmentos unidos em {output_file}")
    
    # Faxina Diamond: Remover fragmentos após consolidar para manter o Curated Store limpo
    logger.info("🧹 Iniciando limpeza de fragmentos temporários...")
    for frag in fragments: 
        try:
            os.remove(frag)
        except Exception as e:
            logger.error(f"⚠️ Erro ao remover fragmento {frag}: {e}")
    
    logger.info("✨ Curated Store limpo e organizado.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python consolidate_dataset.py <caminho_da_missao>")
        sys.exit(1)
        
    consolidate_mission(sys.argv[1])
