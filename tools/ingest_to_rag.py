import os
import sys
from core.ingestor import IngestorAgent
from dotenv import load_dotenv

load_dotenv()

def run_ingest():
    input_file = "data/output/ds_academy_articles_phase2_2026-04-27.jsonl"
    collection = "ds_academy_master"
    
    print(f"--- Iniciando Ingestao Neural: {input_file} ---")
    
    agent = IngestorAgent()
    result = agent.ingest_jsonl_file(input_file, collection)
    
    if result['status'] == 'success':
        print(f"SUCESSO! {result['chunks_count']} vetores injetados na colecao '{collection}'")
    else:
        print(f"AVISO: {result['message']}")

if __name__ == '__main__':
    run_ingest()
