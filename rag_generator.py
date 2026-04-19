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
# ETAPA 0: SELEÇÃO DE CONTEXTO
# ==========================================
print("\nEscolha a base de conhecimento:")
print("1. Notícias (BBC)")
print("2. E-commerce (eBay - Rigido)")
print("3. E-commerce (eBay - Strict)")
print("4. E-commerce (eBay - Strict2)")
escolha = input("Selecione (1, 2, 3 ou 4): ").strip()

if escolha == "1":
    collection_target = "noticias_bbc"
elif escolha == "2":
    collection_target = "market_ebay_rigido"
elif escolha == "3":
    collection_target = "market_ebay_strict"
elif escolha == "4":
    collection_target = "market_ebay_strict2"
else:
    print("Opção inválida.")
    sys.exit(1)

# ==========================================
# ETAPA 1: RETRIEVAL (Buscando os Dados)
# ==========================================
# Conectamos ao banco vetorial que você já populou no passo anterior
client_chroma = chromadb.PersistentClient(path="./vector_db")
ef = embedding_functions.DefaultEmbeddingFunction()

try:
    collection = client_chroma.get_collection(name=collection_target, embedding_function=ef)
    print(f"✅ Coleção '{collection_target}' carregada com sucesso!")
except Exception as e:
    print(f"Erro: Coleção '{collection_target}' não encontrada. Rode o rag_tester.py primeiro.")
    sys.exit(1)

# O "System Prompt" e o que garante que a IA nao vai alucinar.
# Nós construímos uma "jaula de contexto" ao redor dela.
prompt_sistema = """Você é um assistente corporativo de elite.
A sua função é responder à pergunta do usuário baseando-se ÚNICA E EXCLUSIVAMENTE no Contexto fornecido.

Regras Estritas:
1. Se a resposta não estiver contida no contexto, diga exatamente: 'Não possuo informações suficientes no documento para responder a isso.'
2. Não utilize conhecimentos prévios externos.
3. Se o usuário pedir um link ou URL, procure nos metadados fornecidos ou extraia as URLs formatadas em Markdown (ex: [texto](URL)).
4. Seja direto, claro e profissional.
"""

# ==========================================
# LOOP INTERATIVO DE PERGUNTAS
# ==========================================
historico_conversa = [] # Memória de Curto Prazo do Agente

print("\nModulo RAG Interativo pronto. Digite 'sair' ou 'q' para encerrar.")

while True:
    pergunta_do_usuario = input("\nUsuario: ")
    
    if pergunta_do_usuario.lower() in ['sair', 'q', 'exit']:
        print("Encerrando Agente NeuralSafety...")
        break
        
    if not pergunta_do_usuario.strip():
        continue

    # ==========================================
    # O CÉREBRO DE BUSCA: Standalone Query Rewriter
    # ==========================================
    if historico_conversa:
        # Pega as últimas 4 rodadas para ter contexto sem estourar o limite
        contexto_breve = "\n".join([f"{m['role']}: {m['content']}" for m in historico_conversa[-4:]])
        
        prompt_reescrita = f"""Dada a conversa abaixo e a nova pergunta do usuário, reescreva a pergunta para que ela seja uma frase de busca autônoma e completa para um banco de dados. 
        Inclua nomes de produtos, marcas ou especificações técnicas necessárias.
        Não responda a pergunta, APENAS retorne a pergunta reescrita.
        
        Conversa Recente:
        {contexto_breve}
        
        Nova Pergunta do Usuário: {pergunta_do_usuario}
        
        Pergunta Reescrita para Busca:"""

        print("🧠 Traduzindo intenção do usuário (Query Rewriting)...")
        resposta_rewriter = client_llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_reescrita}],
            temperature=0.0 # Máxima precisão
        )
        query_chroma = resposta_rewriter.choices[0].message.content.strip()
        print(f"🔄 Query Otimizada: '{query_chroma}'")
    else:
        query_chroma = pergunta_do_usuario

    print("🔎 Extraindo conhecimento com eficiência de tokens...")
    # Busca no ChromaDB usando a query expandida!
    resultados = collection.query(
        query_texts=[query_chroma],
        n_results=3,
        include=['documents', 'metadatas', 'distances'] 
    )

    # Lógica de Poda de Custo (Top-K Dinâmico)
    LIMITE_DISTANCIA = 1.30 
    chunks_filtrados = []

    for i, distancia in enumerate(resultados['distances'][0]):
        if distancia < LIMITE_DISTANCIA:
            # Pega o texto e o metadado (URL)
            texto_chunk = resultados['documents'][0][i]
            url_origem = resultados['metadatas'][0][i].get('source_url', 'URL não disponível')
            
            # Enriquecimento: Injetamos a URL diretamente no texto para o LLM ver
            chunk_enriquecido = f"--- ORIGEM: {url_origem} ---\n{texto_chunk}"
            
            chunks_filtrados.append(chunk_enriquecido)
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

    # Montagem de Prompt com Memória Linear
    mensagens_llm = [{"role": "system", "content": prompt_sistema}]

    # 1. Injetamos o histórico (se houver) para manter o fio da meada
    for msg in historico_conversa:
        mensagens_llm.append(msg)

    # 2. Injetamos a rodada atual com o contexto extraído
    prompt_atual = f"Contexto Recuperado:\n{contexto_recuperado}\n\nPergunta Atual: {pergunta_do_usuario}"
    mensagens_llm.append({"role": "user", "content": prompt_atual})

    try:
        resposta = client_llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensagens_llm,
            temperature=0.1
        )

        resposta_final = resposta.choices[0].message.content

        print("-" * 50)
        print("Agente NeuralSafety:")
        print(resposta_final)
        print("-" * 50)
        
        # 3. Salva a interação na memória
        historico_conversa.append({"role": "user", "content": pergunta_do_usuario})
        historico_conversa.append({"role": "assistant", "content": resposta_final})

        # MONITOR DE ECONOMIA
        usage = resposta.usage
        print(f"[ECONOMIA] Entrada: {usage.prompt_tokens} | Saida: {usage.completion_tokens} | Total: {usage.total_tokens} tokens")
        print("-" * 50)
        
    except Exception as e:
        print(f"Erro ao chamar a API da OpenAI: {e}")


