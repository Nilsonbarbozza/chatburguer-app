import json
import os
import chromadb
from chromadb.utils import embedding_functions

print("Iniciando Motor RAG Local (ChromaDB)...")

# 1. Carregar o nosso dataset limpo
print("\nSelecione o Dataset para Ingestão:")
print("1. Notícias (BBC)")
print("2. E-commerce (eBay - Rigido)")
print("3. E-commerce (eBay - Strict)")
print("4. E-commerce (eBay - Strict2)")
print("5. Notícias (Finlândia - Strict)")
escolha_dataset = input("Opção (1, 2, 3, 4 e 5): ").strip()

if escolha_dataset == "1":
    caminho_arquivo = "output/bbc/dataset_readable.json"
    collection_name = "noticias_bbc"
    pergunta_teste = "Por que o diesel preocupa o governo e o que foi feito?"
elif escolha_dataset == "2":
    caminho_arquivo = "output/ebay_rigido/dataset_readable.json"
    collection_name = "market_ebay_rigido"
    pergunta_teste = "Qual o carregador de iPhone mais vendido e qual o preço?"
elif escolha_dataset == "3":
    caminho_arquivo = "output/ebay_strict/dataset_readable.json"
    collection_name = "market_ebay_strict"
    pergunta_teste = "Qual o carregador de iPhone mais vendido e qual o preço?"
elif escolha_dataset == "4":
    caminho_arquivo = "output/ebay_strict2/dataset_readable.json"
    collection_name = "market_ebay_strict2"
    pergunta_teste = "Qual a URL de destino do adaptador de 20W?"
elif escolha_dataset == "5":
    caminho_arquivo = "output/finlandia_strict/dataset_readable.json"
    collection_name = "finlandia_strict"
    pergunta_teste = "Qual salario minimo na finlândia?"
else:
    print("Opção inválida.")
    exit()

try:
    if not os.path.exists(caminho_arquivo):
        print(f"Erro: Arquivo {caminho_arquivo} não encontrado. Certifique-se de que o arquivo existe na pasta correspondente.")
        exit()

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Acessa os chunks da primeira (e única) página do nosso teste
    chunks = dados[0]["content"]["semantic_chunks"]
    print(f"Dataset '{collection_name}' carregado com sucesso. {len(chunks)} Chunks encontrados.")
except Exception as e:
    print(f"Erro ao ler o arquivo JSON: {e}")
    exit()

# 2. Inicializar o ChromaDB
client = chromadb.PersistentClient(path="./vector_db")

# Carrega API Key para Embeddings
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Enterprise Embedding Engine (Sincronizado com o Gerador)
ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=api_key,
    model_name="text-embedding-3-small"
)

# Cria (ou carrega) a nossa "gaveta" de vetores
collection = client.get_or_create_collection(
    name=collection_name,
    embedding_function=ef
)

# 3. Preparar os dados para Ingestão
documentos = []
metadados = []
ids = []

print("Vetorizando e Ingerindo dados no banco... (Pode levar uns segundos na 1ª vez)")
for chunk in chunks:
    # Ignora chunks muito curtos ou defeituosos, se houver
    if len(chunk["text"]) < 10:
        continue
        
    documentos.append(chunk["text"])
    metadados.append(chunk["metadata_snapshot"])
    ids.append(f"chunk_{chunk['id']}")

# 4. Inserir no ChromaDB
collection.upsert(
    documents=documentos,
    metadatas=metadados,
    ids=ids
)
print("Ingestão Concluída!\n")

# ==========================================
# 5. TESTE PRÁTICO (Busca Semântica)
# ==========================================
print("Realizando busca semântica...")
pergunta_do_usuario = pergunta_teste

# O ChromaDB vai converter essa pergunta em vetor e buscar os 2 chunks mais próximos
resultados = collection.query(
    query_texts=[pergunta_do_usuario],
    n_results=2
)

# Exibir os resultados formatados
print(f"\n? PERGUNTA: '{pergunta_do_usuario}'\n")

for i in range(len(resultados['documents'][0])):
    print(f"--- RESULTADO {i+1} ---")
    print(f"Origem: {resultados['metadatas'][0][i]['source_url']}")
    # print(f"Tokens Estimados: {resultados['metadatas'][0][i]['token_estimate']}")
    print(f"Texto Recuperado:\n{resultados['documents'][0][i]}\n")
    print("-" * 40)
