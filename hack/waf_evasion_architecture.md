# Doutrina de Evasão Neural: Arquitetura Anti-WAF
Este manifesto detalha as técnicas de guerra utilizadas por Firewalls Aplicacionais Corporativos (Datadome, Cloudflare, Akamai) para corromper extração de dados e as contramedidas exatas para o nosso módulo `core/stages/dataclear.py`.

## 1. Honeypots Anatômicos (Divisórias Pote de Mel)
**Tática do WAF:** Eles injetam blocos HTML estruturais invisíveis (ex: `<div role="main" style="display:none; opacity:0; visibility:hidden;">Temos ofertas!</div>`). Como crawlers primitivos procuram pelo papel (role) sem renderizar o CSS, eles engolem essa isca em vez do texto verdadeiro do site.

**Contramedida (`dataclear.py`):**
A Poda em Cascata Baseada em Densidade (implementada recentemente). Nós não acreditamos apenas no nome da Tag. Nós checamos se o bloco capturado possui um comprimento real de texto puro (`> 200 caracteres`). Para evolução futura: injetar no Playwright uma injeção de JavaScript que delete tags que o navegador afirme estarem com `display: none` ou `opacity: 0` antes de entregar o HTML final para o Python.

## 2. Ofuscação por Fontes (Font Obfuscation Poisoning)
**Tática do WAF:** Sites de nicho (venda de veículos, contatos) enviam textos onde a string bruta viaja como "X$8m@l", mas o site faz o download de um arquivo de fonte (`.woff`) falso onde "X" é desenhado visualmente na tela como a letra "A", "$" como "B", etc. Assim o cliente lê perfeitamente, mas o robô rouba lixo criptografado.

**Contramedida (`dataclear.py`):**
Nosso "Anti-Ofuscação CSS / Sniper de Letras Soltas". Detectar se o texto resultante é apenas ruído desprovido de sentido ou palavras reais do dicionário. No backend, em "Modo Militar Extremo", obrigamos o LLM RAG a reler o site mas desativando totalmente a leitura de fontes Customizadas pelo Playwright forçando o navegador a usar Arial fallback.

## 3. Injeção de "Zero-Width Characters" (Agulhas Invisíveis)
**Tática do WAF:** Inserção de caracteres Unicode como `\u200B` (Zero Width Space) no meio de toda e qualquer palavra do texto. O olho humano não enxerga diferença ("Process-Cloner"), mas o BeautifulSoup e o LLM enxergam "P\u200Br\u200Bo\u200Bc\u200Be\u200Bs\u200Bs". Isso destrói os Vetores e a busca por Similaridade Semântica (Embeddings) não consegue achar a palavra certa.

**Contramedida (`dataclear.py`):**
Nossa linha de Normalização Unicode NFKC.
Nós já iniciamos essa blindagem com a seguinte vacina: 
`markdown_body = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2060-\u206f\xad\ufeff]', '', markdown_body)`
Qualquer veneno invisível inserido para quebrar Embeddings é aspirado e incinerado antes de cair no RAG. 

## 4. Shadow DOM Isolation (O "Container Blindado")
**Tática do WAF:** As partes vitais do texto não existem no código-fonte "Pai" da página. Eles abrigam o texto valioso dentro de "Shadow DOMs" fechados. O `BeautifulSoup` (Motor central Python do nosso DataClear) tropeça na Tag Pai e vê apenas "vazio". Por debaixo dos panos, o navegador desenha um site complexo, mas para o Scraper, o arquivo JSON volta vazio (ou 0 chunks).

**Contramedida (`dataclear.py` / `html_processor.py`):**
Neste cenário, a modificação precisa ocorrer ANTES do dataclear. O script de extração Javascript no Playwright deve conter a diretiva `.innerHTML` recursiva capaz de atravessar componentes Shadow (como Web Components) e injetar seus resultados textuais à força no DOM raíz.

## 5. Tarpitting Intersticial (Desafio 5 Segundos Cloudflare)
**Tática do WAF:** Quando acessamos o site, o Payload recebido é de fato HTML (com tags Título, Body e Scripts). No entanto, essas tags não contêm o blog/produto. Elas geram um portal de desafio: "Checking if the site connection is secure". O Scraper extrai o HTML desse portal de validação pensando ser o dado valioso e encerra a consulta antes da passagem de permissão.

**Contramedida (`Scraper Stage` + `rag_generator.py`):**
Nosso mecanismo de travamento síncrono que bloqueia respostas HTTP. Em breve, a inteligência do Playwright (`ScraperStage`) deve incorporar "Wait-For" selectors, onde forçamos o robô a não tirar a "foto" do HTML enquanto existirem classes como `.cf-challenge`, garantindo que o texto a chegar no `DataClear` seja real e denso.

---

### 🔥 Princípio Arquitetural de Adaptação
A principal força de defesa contra um Firewall não é bater de frente com a criptografia dele, mas **filtrar o resultado esperado na Extração Semântica**. O nosso `dataclear.py` está desenhado para assumir que tudo vindo da Web Web está comprometido e hostil. Como demonstrado no caso das DIVs falsas, Heurísticas de Densidade (peso do texto > 200 caracteres) são imensamente mais eficientes que caçar CSS individualmente.
