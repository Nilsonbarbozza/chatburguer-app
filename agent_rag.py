import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Carrega as chaves do .env local
load_dotenv()

# Configurações do Cliente (Simulando o ambiente do cliente)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("🚨 Erro: OPENAI_API_KEY não encontrada no .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# Configurações da Nossa API (Ajustado para bater exatamente na nossa arquitetura)
NEURALSAFETY_API_URL = "http://localhost:8000/api/v1/fetch"
NEURALSAFETY_API_KEY = "sk-neuralsafety-enterprise-v1" # Chave real definida no auth.py

def neuralsafety_webfetch(url: str, force_stealth: bool = False) -> str:
    """Função que o cliente usa para bater na nossa API e pegar o Markdown."""
    print(f"\n[⚡ AGENTE] Acionando NeuralSafety API para interceptar: {url}")
    
    # Header configurado no nosso auth.py: APIKeyHeader(name="X-API-Key")
    headers = {
        "X-API-Key": NEURALSAFETY_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "force_stealth": force_stealth,
        "render_js": False # Opcional, dependendo da necessidade do Agente
    }
    
    try:
        response = requests.post(NEURALSAFETY_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print(f"[✅ NEURALSAFETY] Extração concluída em {data.get('processing_ms')}ms usando {data.get('executor_used')}")
        return data["markdown_body"]
    
    except Exception as e:
        print(f"[❌ ERRO] Falha na NeuralSafety API: {e}")
        return "Erro: Não foi possível acessar o site devido a um bloqueio extremo de segurança ou servidor offline."

# O Schema que mostraremos nas reuniões comerciais
tools = [
    {
        "type": "function",
        "function": {
            "name": "neuralsafety_webfetch",
            "description": "Extrai conteúdo de artigos, notícias e sites corporativos em Markdown limpo, burlando firewalls (WAF). Use SEMPRE que o usuário fornecer uma URL ou perguntar sobre um site específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "A URL completa do alvo."
                    },
                    "force_stealth": {
                        "type": "boolean",
                        "description": "Defina como true para usar evasão pesada em sites protegidos por Cloudflare/WAF."
                    }
                },
                "required": ["url"]
            }
        }
    }
]

def run_agent(user_query: str):
    print(f"\n👤 Usuário: {user_query}")
    
    messages = [
        {
            "role": "system", 
            "content": "Você é um assistente de pesquisa corporativa de elite. Resuma artigos de forma profissional e analítica. Se precisar de contexto de uma URL, use a ferramenta neuralsafety_webfetch para extrair o conteúdo real."
        },
        {"role": "user", "content": user_query}
    ]

    # 1ª Chamada à OpenAI: O modelo decide se usa a ferramenta
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Se o LLM decidiu usar a nossa API...
    if tool_calls:
        messages.append(response_message) # Anexa a decisão ao histórico
        
        for tool_call in tool_calls:
            if tool_call.function.name == "neuralsafety_webfetch":
                # Extrai os argumentos que o LLM gerou
                args = json.loads(tool_call.function.arguments)
                
                # Executa a nossa API Síncrona
                markdown_result = neuralsafety_webfetch(
                    url=args.get("url"), 
                    force_stealth=args.get("force_stealth", False)
                )
                
                # Injeta o Markdown Puro de volta na mente do LLM
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "neuralsafety_webfetch",
                    "content": markdown_result
                })
        
        print("\n[🧠 AGENTE] Lendo o Markdown extraído e gerando a resposta analítica final...\n")
        
        # 2ª Chamada à OpenAI: O modelo agora leu o site e vai responder
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        print(f"🤖 Resposta Final:\n{final_response.choices[0].message.content}")

    else:
        # Se não precisou de ferramenta, responde direto
        print(f"🤖 Resposta Final:\n{response_message.content}")

# ==========================================
# EXECUTANDO O TESTE REAL
# ==========================================
if __name__ == "__main__":
    # Teste de Estresse Comercial
    alvo = "https://blog.dsacademy.com.br/7-maneiras-que-os-cientistas-de-dados-usam-estatistica/"
    pergunta = f"Leia este artigo ({alvo}) e me explique resumidamente como a estatistica é utilizada na ciencia de dados."
    
    run_agent(pergunta)
