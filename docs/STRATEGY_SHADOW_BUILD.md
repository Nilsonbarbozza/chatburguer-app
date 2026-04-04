# Estratégia de Otimização: Shadow Build (Granular)

A estratégia **Shadow Build** foi desenvolvida para permitir a otimização agressiva de ativos (CSS/JS) em projetos complexos que utilizam classes dinâmicas (Tailwind, Radix UI), minimizando o risco de quebra visual em produção.

## 🎯 Objetivo

Reduzir o peso dos ativos globais (especialmente o `styles.css`) sem afetar a disponibilidade do site original até que a nova versão esteja 100% validada.

---

## 🛠️ Pilares da Estratégia

### 1. Safelist "Couraçada" (Proteção Total)

Diferente de um PurgeCSS padrão, configuramos uma lista de proteção radical que ignora:

- **Prefixos do Framework:** `/^tw-/` (Protege todas as utilidades do Tailwind).
- **Estados Dinâmicos:** `/data-state/`, `/aria-/`, `/data-active/` (Protege componentes que mudam via JS).
- **Identificadores de Design:** `/^inline_/` (Protege classes específicas do sistema de design local).

### 2. Ambiente de Sombra (Isolamento)

Em vez de substituir o arquivo `index.html`, criamos um **clone de validação**:

- **Original:** `index.html` → Consome `styles.css` (758KB).
- **Sombra:** `tester.html` → Consome `styles.safe.css` (299KB).

Isso permite que desenvolvedores e stakeholders visualizem e interajam com a versão otimizada em tempo real, lado a lado com a original.

### 3. Validação por Comparação (Pixel-Match)

Usamos agentes de navegação para comparar capturas de tela e logs de console entre as duas versões:

- **Check de Layout:** Verificação de quebras em resoluções Desktop e Mobile.
- **Check de Interação:** Teste de abertura de modais e menus colapsáveis nas duas versões.

---

## 🐍 Implementação para Automação (Script de Clonação/Python)

Para que um script de automação (Python ou Node) possa replicar essa estratégia com segurança, deve-se seguir estas especificações técnicas:

### 1. Motor de Purge (Estatístico vs. Dinâmico)

O script deve escanear múltiplos arquivos de entrada para construir o mapa de dependências:

- **Arquivos Estáticos:** `index.html`, `tester.html`.
- **Arquivos Dinâmicos (Source Code):** Todos os arquivos `.js` em `scripts/` e subpastas.
- **Regex de Extração Recomendada:** `[\w-/:]+(?<!:)` (Captura nomes de classes Tailwind complexas, incluindo estados como `hover:`, `md:`, etc).

### 2. Regex de Safelist Imperativa (O Ponto Crítico)

Ao clonar sites que usam Tailwind Moderno ou Radix, o script **DEVE** incluir estas proteções no motor de Purge:

```python
# Exemplo de lógica de Safelist para o Script Python
safelist = {
    "standard": [
        r"^tw-",           # Utility classes (Tailwind Prefix)
        r"^inline_",       # Local Design System classes
        r"^data-",         # State attributes (Radix UI)
        r"^aria-",         # Accessibility states
        "active", "open", "closed", "hidden", "visible" # Runtime classes
    ],
    "deep": [
        r"radix",
        r"data-state",     # Crucial para modais e tabs
        r"data-orientation"
    ]
}
```

### 3. Pipeline de "Shadow Output"

O script não deve substituir o arquivo original imediatamente. O fluxo sugerido é:

1.  **Extract:** Carregar CSS original.
2.  **Generate Shadow:** Criar um arquivo único temporário `styles/styles.safe.css`.
3.  **Inject Shadow:** Criar uma cópia do HTML chamada `tester.html` apontando para o CSS novo.
4.  **Health Check:** O script pode rodar uma ferramenta de verificação visual (como Playwright ou Selenium) para comparar as duas páginas.

### 4. Gestão de SVGs (Sprite Policy)

Se o script Python fizer a extração de SVGs inline para Sprites:

- **Erro a Evitar:** Não usar regex ganancioso `[\s\S]*` que pode capturar tags irmãs (ex: `<span>`).
- **Recomendação:** Usar parseadores de árvore DOM (como BeautifulSoup em Python) em vez de regex puro para isolar somente os nós `<svg>`.

---

## 📈 Resultados Obtidos no Projeto Playground AI

| Métrica             | Original   | Otimizado (Shadow)          | Melhora    |
| :------------------ | :--------- | :-------------------------- | :--------- |
| **Peso do CSS**     | 758.13 KB  | 299.78 KB                   | **-60.4%** |
| **Estabilidade**    | 100%       | 100%                        | Mantida    |
| **Risco de Quebra** | Médio/Alto | **Zero** (Ambiente Isolado) | -          |

---

## 🚀 Próximos Passos para o Cloner

1.  Integrar a lógica de **Safelist** acima no loop de limpeza de CSS.
2.  Sempre gerar um **Tester Ambiente** antes de finalizar a clonagem.
3.  Validar contra estados de "hover" e "click" (que costumam carregar classes dinâmicas).
