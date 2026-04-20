import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000/chat"
SESSION_ID = "stress_test_memory_01"
COLLECTION = "market_ebay_strict"

def test_summarization_flow():
    print(f"\n--- INICIANDO TESTE DE SUMARIZAÇÃO ATIVA ---")
    
    # 1. Lista de mensagens para encher a memória (mais de 6 mensagens)
    conversa = [
        "Oi, meu nome é Nilson e eu trabalho com arquitetura de software na Finlândia.",
        "Meu time está desenvolvendo o sistema NeuralSafety.",
        "Nós usamos Python e FastAPI para o back-end.",
        "O nosso banco vetorial de escolha é o ChromaDB.",
        "A OpenAI fornece os modelos gpt-4o-mini e text-embedding-3-small.",
        "O projeto começou em Janeiro de 2026.",
        "Nesta fase, estamos testando o Sliding Window Memory.",
        "O limite de mensagens brutas está configurado para 6 neste teste."
    ]

    for i, msg in enumerate(conversa):
        print(f"\n[Turno {i+1}] Enviando: {msg}")
        payload = {
            "session_id": SESSION_ID,
            "message": msg,
            "collection": COLLECTION
        }
        
        try:
            start_time = time.time()
            res = requests.post(BASE_URL, json=payload, timeout=30)
            elapsed = time.time() - start_time
            
            if res.status_code == 200:
                print(f"OK: Resposta recebida ({elapsed:.2f}s)")
            else:
                print(f"ERRO na API: {res.status_code} - {res.text}")
                return
        except Exception as e:
            print(f"FALHA ao conectar ao servidor: {e}")
            print("Certifique-se de que o servidor está rodando em http://127.0.0.1:8000")
            return

    # 2. Pergunta Filinal: Testando a Memória de Longo Prazo (que já deve estar sumarizada)
    print("\n--- TESTANDO RECUPERAÇÃO DO PASSADO SUMARIZADO ---")
    pergunta_final = "Onde eu trabalho e quando o projeto NeuralSafety começou?"
    
    payload = {
        "session_id": SESSION_ID,
        "message": pergunta_final,
        "collection": COLLECTION
    }
    
    res = requests.post(BASE_URL, json=payload, timeout=30)
    if res.status_code == 200:
        texto_final = res.json()["response"]
        print(f"\n🤖 Resposta da IA: {texto_final}")
        
        # Verificação lógica: a resposta deve conter "Finlândia" e "Janeiro de 2026"
        if "Finlândia" in texto_final and "Janeiro" in texto_final:
            print("\nOK: A IA manteve o contexto após a sumarização ativa!")
        else:
            print("\nALERTA: A IA pode ter perdido detalhes após a compressão.")
    else:
        print(f"❌ Erro no teste final: {res.status_code}")

if __name__ == "__main__":
    # Espera um pouco para garantir que o servidor subiu
    print("Aguardando 3 segundos para estabilidade do servidor...")
    time.sleep(3)
    test_summarization_flow()
