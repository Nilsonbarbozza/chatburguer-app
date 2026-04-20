import os
import sys
# Adiciona o diretório atual ao path para importar o core
sys.path.append(os.getcwd())

from core.memory_manager import SlidingWindowMemory
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client_llm = OpenAI(api_key=api_key)

def test_persistence():
    print("\n--- INICIANDO TESTE DE PERSISTÊNCIA ---")
    
    # 1. Instanciamos a memória (Apagando o banco antigo se existir para teste limpo)
    if os.path.exists("sessions.db"):
        os.remove("sessions.db")
    
    memoria = SlidingWindowMemory(client_llm=client_llm, db_path="sessions.db")
    session_id = "user_enterprise_01"
    
    print(f"1. Criando nova interação para a sessão: {session_id}")
    memoria.add_interaction(
        session_id=session_id, 
        user_msg="Olá, eu sou o Nilson e estou testando a memória.", 
        ai_msg="Olá Nilson! Entendido, estou registrando que você é o Nilson."
    )
    
    # 2. Simulando "Queda do Servidor" (Deletando a instância da memória)
    print("2. [ALERTA] Simulando queda do servidor... (Instância removida da RAM)")
    del memoria
    
    # 3. Reiniciando o sistema e reconectando ao mesmo Banco SQLite
    print("3. Reiniciando sistema e reconectando ao sessions.db...")
    nova_memoria = SlidingWindowMemory(client_llm=client_llm, db_path="sessions.db")
    
    # 4. Verificando se a IA ainda sabe quem é o usuário
    print("4. Recuperando histórico para validar persistência...")
    mensagens = nova_memoria.get_messages(
        session_id=session_id,
        system_prompt="Você é um assistente.",
        context_rag="Nenhum contexto.",
        current_query="Quem sou eu?"
    )
    
    # Validação: A mensagem de 'role: assistant' com o nome 'Nilson' deve estar na lista
    confirmado = False
    for msg in mensagens:
        if "Nilson" in msg.get("content", ""):
            print(f"✅ SUCESSO: Memória recuperada! Conteúdo encontrado: '{msg['content']}'")
            confirmado = True
            break
            
    if not confirmado:
        print("❌ FALHA: A memória foi perdida na reinicialização.")

if __name__ == "__main__":
    test_persistence()
