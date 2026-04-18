import chromadb
from chromadb.utils import embedding_functions
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis do .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key == "sk-sua-chave-aqui":
    print("Erro: OPENAI_API_KEY nao configurada no arquivo .env")
    print("Por favor, insira sua chave real no arquivo .env antes de rodar este script.")
    sys.exit(1)

client_llm = OpenAI(api_key=api_key)

print("Iniciando Motor RAG Completo (Retrieval + Generation)...")

# ==========================================
# ETAPA 1: RETRIEVAL (Buscando os Dados)
# ==========================================
# Conectamos ao banco vetorial que você já populou no passo anterior
client_chroma = chromadb.PersistentClient(path="./vector_db")
ef = embedding_functions.DefaultEmbeddingFunction()

try:
    collection = client_chroma.get_collection(name="noticias_bbc", embedding_function=ef)
except Exception as e:
    print("Erro: Coleção 'noticias_bbc' nao encontrada. Rode o rag_tester.py primeiro.")
    sys.exit(1)

# O "System Prompt" e o que garante que a IA nao vai alucinar.
# Nós construímos uma "jaula de contexto" ao redor dela.
prompt_sistema = """Você é um assistente corporativo de elite.
A sua função é responder à pergunta do usuário baseando-se ÚNICA E EXCLUSIVAMENTE no Contexto fornecido.

Regras Estritas:
1. Se a resposta não estiver contida no contexto, diga exatamente: 'Não possuo informações suficientes no documento para responder a isso.'
2. Não utilize conhecimentos prévios externos.
3. Seja direto, claro e profissional.
"""

# ==========================================
# LOOP INTERATIVO DE PERGUNTAS
# ==========================================
print("\nModulo RAG Interativo pronto. Digite 'sair' ou 'q' para encerrar.")

while True:
    pergunta_do_usuario = input("\nUsuario: ")
    
    if pergunta_do_usuario.lower() in ['sair', 'q', 'exit']:
        print("Encerrando Agente NeuralSafety...")
        break
        
    if not pergunta_do_usuario.strip():
        continue

    print("Extraindo conhecimento com eficiencia de tokens...")
    # Solicitamos ao Chroma que retorne também as 'distances'
    resultados = collection.query(
        query_texts=[pergunta_do_usuario],
        n_results=3,
        include=['documents', 'metadatas', 'distances'] 
    )

    # Lógica de Poda de Custo (Top-K Dinâmico)
    # O limite depende do seu dataset, mas 1.2 é um bom ponto de corte para L2
    LIMITE_DISTANCIA = 1.30 
    chunks_filtrados = []

    for i, distancia in enumerate(resultados['distances'][0]):
        if distancia < LIMITE_DISTANCIA:
            chunks_filtrados.append(resultados['documents'][0][i])
            print(f"OK: Chunk {i+1} aprovado para o LLM | Distancia: {distancia:.4f}")
        else:
            print(f"Corte: Chunk {i+1} descartado para economizar tokens | Distancia: {distancia:.4f}")

    # Prepara o contexto final (se não sobrar nenhum, passamos vazio para o LLM negar)
    if not chunks_filtrados:
        contexto_recuperado = "Nenhum contexto relevante encontrado no documento."
    else:
        contexto_recuperado = "\n\n".join(chunks_filtrados)

    print(f"Economia: Enviando apenas {len(chunks_filtrados)} chunk(s) para processamento.\n")


    # ==========================================
    # ETAPA 2: GENERATION (A Magica da IA)
    # ==========================================
    print("Injetando contexto no LLM e gerando resposta...\n")

    # Injetamos os dados brutos destilados pelo seu Cloner CLI na mensagem do usuário
    prompt_usuario = f"Contexto:\n{contexto_recuperado}\n\nPergunta: {pergunta_do_usuario}"

    try:
        resposta = client_llm.chat.completions.create(
            model="gpt-4o-mini", # Modelo rápido e barato para RAG
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.1 # Temperatura baixíssima = Respostas lógicas e não criativas (Foco em precisão)
        )

        print("-" * 50)
        print("Agente NeuralSafety:")
        print(resposta.choices[0].message.content)
        print("-" * 50)
        
        # MONITOR DE ECONOMIA
        usage = resposta.usage
        print(f"[ECONOMIA] Entrada: {usage.prompt_tokens} | Saida: {usage.completion_tokens} | Total: {usage.total_tokens} tokens")
        print("-" * 50)
        
    except Exception as e:
        print(f"Erro ao chamar a API da OpenAI: {e}")


