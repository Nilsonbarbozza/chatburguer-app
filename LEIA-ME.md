# Process Cloner v1.0 — Guia Rápido

Bem-vindo! Este guia explica como usar o Process Cloner em 3 passos.

---

## 📋 Pré-requisitos

- **Python 3.9+** instalado ([python.org](https://www.python.org/downloads/))
- **Node.js 18+** instalado ([nodejs.org](https://nodejs.org)) *(opcional, mas recomendado)*

---

## 🚀 Instalação

### Windows
Dê duplo clique em `install.bat`

### Linux / macOS
```bash
chmod +x install.sh
./install.sh
```

---

## 🔄 Fluxo de Uso

### Passo 1 — Capturar o site no navegador

Instale a extensão **SingleFile** no seu navegador:
- [Chrome](https://chrome.google.com/webstore/detail/singlefile/)
- [Firefox](https://addons.mozilla.org/pt-BR/firefox/addon/single-file/)

Acesse o site que deseja usar como referência e clique em **SingleFile** para baixar o arquivo `.html`.

---

### Passo 2 — Processar com o Process Cloner

Abra o terminal na pasta do programa e execute:

```bash
python cloner.py
```

Quando solicitado, arraste o arquivo `.html` que você baixou para o terminal, ou cole o caminho completo.

---

### Passo 3 — Usar com LLM ou agente de código

Após o processamento, a pasta `output/` conterá:

```
output/
├── index.html          ← estrutura limpa e organizada
├── styles/styles.css   ← todos os estilos consolidados
├── scripts/main.js     ← scripts organizados
├── images/             ← imagens extraídas
└── skills/frontend.md  ← 🧠 contexto para LLM
```

**Usando com Claude Code:**
```bash
# Na pasta output/, execute:
claude
# Prompt sugerido:
# "Analise os arquivos desta pasta. Use o frontend.md como referência
#  de design. Quero criar [SEU PROJETO]. Comece pelo index.html."
```

**Usando com ChatGPT / Gemini:**
1. Abra o chat da LLM
2. Faça upload dos arquivos da pasta `output/`
3. Use o prompt sugerido no arquivo `skills/frontend.md`

---

## ⚙️ Configuração Avançada

Edite o arquivo `.env` para personalizar o comportamento:

| Variável | Padrão | Descrição |
|---|---|---|
| `OUTPUT_DIR` | `output` | Pasta de saída |
| `MINIFY_CSS` | `false` | Minificar CSS |
| `BUNDLE_SCRIPTS` | `true` | Agrupar scripts |
| `USE_TAILWIND` | `false` | Injetar Tailwind CDN |

---

## ❓ Problemas comuns

**"Módulo não encontrado"**  
Execute `pip install -r requirements.txt` novamente.

**"Prettier não encontrado"**  
O HTML ainda será gerado, apenas sem formatação premium. Instale com `npm install -g prettier`.

**Imagens não carregam**  
Informe a URL base do site quando solicitado pelo programa.

---

## 📞 Suporte

Em caso de dúvidas, acesse os vídeos tutoriais incluídos na pasta `aulas/`.

---

*Process Cloner v1.0 — Licença de uso pessoal inclusa em LICENSE.md*
