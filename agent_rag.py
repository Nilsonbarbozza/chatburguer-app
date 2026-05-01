import os
import json
import requests
from openai import OpenAI

# ==========================================
# CONFIGURAÇÕES
# ==========================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-sua-chave-da-openai-aqui")
if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-sua-chave-da-openai-aqui":
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Nossa API Batalhão
NEURALSAFETY_API_URL_FETCH = "http://localhost:8000/api/v1/fetch"
NEURALSAFETY_API_URL_SEARCH = "http://localhost:8000/api/v1/search_and_fetch"
NEURALSAFETY_API_KEY = "sk-neuralsafety-enterprise-v1"

# ==========================================
# CONECTORES DA NOSSA API
# ==========================================
def neuralsafety_webfetch(url: str, force_stealth: bool = False) -> str:
    """Ferramenta 1: Extração Direta (Quando já temos o link)"""
    print(f"\n[⚡ TÁTICA 1] Acionando WebFetch Direto para: {url}")
    headers = {"X-API-Key": NEURALSAFETY_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(NEURALSAFETY_API_URL_FETCH, json={"url": url, "force_stealth": force_stealth}, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"[✅ NEURALSAFETY] Extração Limpa em {data.get('processing_ms')}ms")
        return data["markdown_body"]
    except Exception as e:
        return f"Erro na extração: {e}"

def neuralsafety_search_and_fetch(query: str, force_stealth: bool = False) -> str:
    """Ferramenta 2: O Tiro Único (Radar Tavily + Extração Simultânea)"""
    print(f"\n[📡 TÁTICA 2] Acionando Radar + Tiro Único para a query: '{query}'")
    headers = {"X-API-Key": NEURALSAFETY_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(NEURALSAFETY_API_URL_SEARCH, json={"query": query, "force_stealth": force_stealth}, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"[✅ NEURALSAFETY] Busca e Extração Simultânea concluída em {data.get('processing_ms')}ms. URLs processadas: {data.get('urls_processed')}")
        return data["consolidated_markdown"]
    except Exception as e:
        return f"Erro no Radar: {e}"

# ==========================================
# ARSENAL DO AGENTE (TOOLS)
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "neuralsafety_webfetch",
            "description": "Extrai o conteúdo de uma URL específica em Markdown limpo. Use SEMPRE que o usuário fornecer um link exato no chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": { "type": "string", "description": "A URL completa do alvo." },
                    "force_stealth": { "type": "boolean", "description": "Ativar se houver proteções severas." }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "neuralsafety_search_and_fetch",
            "description": "Busca na internet por eventos recentes e extrai o conteúdo das duas melhores fontes. Use quando o usuário fizer perguntas sobre notícias, eventos atuais ou pedir pesquisas SEM fornecer um link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "A frase de busca otimizada (ex: 'novas regulamentações de IA na Europa 2026')." },
                    "force_stealth": { "type": "boolean" }
                },
                "required": ["query"]
            }
        }
    }
]

# ==========================================
# CÉREBRO DO AGENTE (LOOP DE ROTEAMENTO)
# ==========================================
def run_agent(user_query: str):
    print(f"\n👤 Usuário: {user_query}")
    
    messages = [
        {"role": "system", "content": "Você é um analista de inteligência corporativa. Você DEVE usar suas ferramentas de WebFetch para buscar contexto antes de responder. Não adivinhe dados recentes."},
        {"role": "user", "content": user_query}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            # ROTEADOR MÁGICO DO LLM
            if tool_call.function.name == "neuralsafety_webfetch":
                args = json.loads(tool_call.function.arguments)
                result = neuralsafety_webfetch(url=args.get("url"), force_stealth=args.get("force_stealth", False))
                
            elif tool_call.function.name == "neuralsafety_search_and_fetch":
                args = json.loads(tool_call.function.arguments)
                result = neuralsafety_search_and_fetch(query=args.get("query"), force_stealth=args.get("force_stealth", False))
            
            # Injeta o resultado de volta
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_call.function.name,
                "content": result
            })
        
        print("\n[🧠 AGENTE] Lendo dados táticos e gerando a síntese...\n")
        final_response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        print(f"🤖 Resposta Final:\n{final_response.choices[0].message.content}")

    else:
        print(f"🤖 Resposta Final:\n{response_message.content}")

# ==========================================
# TESTES DE MESA (O CAMPO DE PROVA)
# ==========================================
if __name__ == "__main__":
    print("--- INICIANDO TESTE DE ROTEAMENTO ---")
    
    # Teste 1: O cliente dá a URL (Deve acionar TÁTICA 1)
    # run_agent("Resuma os pontos principais deste artigo: https://blog.dsacademy.com.br/o-que-e-machine-learning/")
    
    # Teste 2: O cliente não dá a URL (Deve acionar TÁTICA 2)
    run_agent("Quais são as notícias mais recentes de hoje sobre o avanço da Inteligência Artificial em mineração?")
