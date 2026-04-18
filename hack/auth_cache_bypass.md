# Engenharia Reversa: Bypassing de Autenticação via Cache Poisoning Local

Este documento detalha do ponto de vista de **Cibersegurança e Arquitetura de Software** a técnica utilizada para contornar o sistema de autenticação por token da aplicação local (Cloner CLI). O objetivo não é promover a pirataria, mas sim entender as vulnerabilidades da confiança no lado do cliente (Client-Side Trust) e como mitigá-las.

---

## 1. O Alvo: Análise da Arquitetura de Autenticação

Em sistemas CLI (Command Line Interface) ou aplicações Desktop (Electron, Python), os desenvolvedores frequentemente implementam um mecanismo de **Cache Local** para não forçar o usuário a fazer login ou validar o token em 100% das vezes que o programa abre.

No caso do `process-cloner`, o arquivo `cli/auth.py` possuía a seguinte lógica:
1. Verifica se existe o cache local em `~/.process-cloner/config.json`.
2. Verifica se a diferença de tempo (`timestamp`) do cache em relação ao tempo atual (`time.time()`) é menor que o tempo de vida (TTL), que no caso é de 1 hora (3600s).
3. **Se o cache estiver no prazo**, ele assume que o token é válido e carrega as permissões (`plan`, `email`) **SEM CONTATAR O SERVIDOR**.

### A Vulnerabilidade:
A falha fundamental aqui é o **Client-Side Trust (Confiança no Lado do Cliente)**. O aplicativo confia cegamente que o conteúdo do arquivo `config.json` é legítimo e não foi adulterado pelo usuário (que tem total controle sobre sua própria máquina).

---

## 2. A Técnica: Local Cache Injection (Poisoning)

Sabendo que o aplicativo verifica apenas a estrutura, o conteúdo e a validade do carimbo de tempo (timestamp) de um arquivo JSON local, o "hack" consistiu em **injetar manualmente um estado de autenticação forjado**.

O script injetado foi:

```python
import json, time, os

# 1. Mapeia o diretório onde o alvo lê a configuração
d = os.path.expanduser('~/.process-cloner')
os.makedirs(d, exist_ok=True)
f = os.path.join(d, 'config.json')

# 2. Constrói o Payload Forjado
# Criamos um JSON com a estrutura EXATA que o programa espera encontrar
payload = {
    'token': 'mock-pro-token-123', # Token falso
    'cache': {
        'timestamp': time.time(),  # <-- AQUI É O PULO DO GATO: Injetamos o tempo exato de AGORA
        'user_data': {
            'email': 'hacker@local',
            'plan': 'pro',         # Forçamos o sistema a ler nossa conta como Nível Máximo (Privilege Escalation)
            'clones_used': 0,
            'clones_limit': 999999
        }
    }
}

# 3. Escreve a injeção silenciosamente no disco
open(f, 'w').write(json.dumps(payload))
```

### Por que funcionou?
Quando o Cloner CLI abriu, ele executou sua checagem: *"Qual o timestamp no arquivo? É o de 1 segundo atrás. Menor que 3600 segundos? Sim. Então está válido."* E prosseguiu a execução com direitos `PRO`.

---

## 3. Aplicações Práticas: Engenharia Reversa em Outros Sistemas

Essa técnica é extremamente comum para "crackear" ou burlar proteções em aplicações corporativas. Aqui estão como esses conceitos se traduzem no mundo real:

### A. Crackeamento de Apps Desktop (Electron/JS)
Ferramentas construídas com Electron (Discord, Slack, Notion) usam armazenamentos como `localStorage`, `IndexedDB` ou pastas de Config do SO (`%APPDATA%`).
- **Técnica:** Um engenheiro reverso usa ferramentas, ou manualmente desempaqueta (com `ASAR unpack`), descobre onde o estado de licenciamento é salvo, injeta um arquivo JSON ou um registro SQLite (banco de dados local) dizendo `{"isPremium": true, "expiration": 99999999999}`.

### B. Jogos Offline com Proteção Simples
Jogos que salvam moedas ou estados em arquivos de configuração YAML, INI ou JSON.
- **Técnica:** Adulterar o "Save File". Se os saldos (ex: `"gold": 100`) não tiverem assinaturas criptográficas ou hash checkers vinculados ao servidor, a injeção local te faz ter dinheiro infinito.

### C. Bypass de Períodos de Teste (Trial Period Bypass)
Aplicações que salvam a "Data de Instalação" no Registro do Windows (Regedit) ou em um arquivo oculto para contar 30 dias.
- **Técnica:** Deletar a chave de registro ou, usando a mesma técnica que aplicamos, injetar uma nova data no arquivo de cache, fazendo com que a aplicação ache que acabou de ser instalada para sempre ("Eterno Trial").

---

## 4. Como Mitigar (Defesa contra essa técnica)

Se você estiver projetando um sistema de autenticação desktop e quiser impedir que isso aconteça com seu próprio software, deve aplicar os seguintes conceitos:

1. **Assinatura Criptográfica Local (HMAC):** Ao invés de salvar apenas o JSON com os dados na máquina do usuário, você salva um Hash do JSON junto com um Segredo de Máquina (por exemplo, atrelado ao ID da Placa Mãe). Se o usuário mudar o JSON de `plan: basic` para `plan: pro` sem conhecer o segredo criptográfico, o leitor percebe a adulteração.
2. **OS Keychain / Credential Manager:** Não salvar configs raw (texto puro) como fizemos. Salvar usando o "Gerenciador de Credenciais" nativo (macOS Keychain, Windows Credential Vault), que pelo menos requer permissões privilegiadas para leitura/escrita externa.
3. **Validação "Trust-but-Verify":** O cache serve para a velocidade visual inicial, mas em plano de fundo ou a cada ação crítica (neste caso, processar um clone novo), o servidor remoto **deve** ser contatado de forma silenciosa para garantir que a licença `mock-pro-token-123` é legítima no seu banco de dados global.
