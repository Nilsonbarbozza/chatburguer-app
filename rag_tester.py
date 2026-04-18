import json
import os
import chromadb
from chromadb.utils import embedding_functions

print("Iniciando Motor RAG Local (ChromaDB)...")

# 1. Carregar o nosso dataset limpo
# Substitua o caminho se o seu arquivo estiver em outra pasta
caminho_arquivo = "output/dataset_readable.json"

try:
    if not os.path.exists(caminho_arquivo):
        print(f"Erro: Arquivo {caminho_arquivo} nao encontrado. Por favor, execute o cloner primeiro.")
        exit()

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    # Acessa os chunks da primeira (e única) página do nosso teste
    chunks = dados[0]["content"]["semantic_chunks"]
    print(f"Dataset carregado com sucesso. {len(chunks)} Chunks encontrados.")
except Exception as e:
    print(f"Erro ao ler o arquivo JSON: {e}")
    exit()

# 2. Inicializar o ChromaDB (Persistente para não precisar recriar toda vez)
# Ele criará uma pasta "vector_db" localmente
client = chromadb.PersistentClient(path="./vector_db")

# Usando o modelo padrão do Chroma para gerar os embeddings automaticamente
ef = embedding_functions.DefaultEmbeddingFunction()

# Cria (ou carrega) a nossa "gaveta" de vetores
collection = client.get_or_create_collection(
    name="noticias_bbc",
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
pergunta_do_usuario = "Por que o diesel preocupa o governo e o que foi feito?"

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
