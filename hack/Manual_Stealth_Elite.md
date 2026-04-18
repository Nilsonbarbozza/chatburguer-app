# 🛡️ Manual de Engenharia Stealth de Elite (Cloner CLI)

Este manual consolida a inteligência tática desenvolvida durante os testes de estresse em portais de alta segurança (Reuters, Google Maps, UKKO.fi). Siga estas diretrizes para manter a **furtividade total** e a **extrema confiabilidade** dos dados.

---

## 🏗️ A Hierarquia dos Bloqueios (O "Iceberg")

Para vencer um firewall como Akamai ou DataDome, você deve entender que o bloqueio acontece em camadas. Se você falhar na primeira, as outras nem são avaliadas.

1.  **Nível 1: Reputação de IP (O Muro)**
    *   **O que é:** O Firewall olha o seu endereço IP. Se houver muitos acessos de automação, ele entra em *Hard Blacklist*.
    *   **Sintoma:** Você recebe erros `401`, `403` ou uma página de 1.500 bytes instantaneamente.
    *   **Solução:** Trocar de WiFi, usar 4G ou **Proxies Residenciais Rotativos**.

2.  **Nível 2: Fingerprint TLS (A Assinatura)**
    *   **O que é:** O modo como o Chromium se comunica na rede ("aperto de mão").
    *   **Defesa Cloner:** Usamos a versão **Chrome 124+** e spoofing de `User-Agent` para parecer um navegador de usuário real atualizado.

3.  **Nível 3: Heurística Comportamental (O Teste de Turing)**
    *   **O que é:** O site observa como você move o mouse e rola a página. Bots movem-se em linha reta; humanos tremem e oscilam.
    *   **Defesa Cloner:** Implementamos **Curvas de Bézier** e **Scroll com Overshoot**.

---

## 🛠️ Arsenal Tático Integrado

### 1. Ghost Cursor (Biometria de Mouse)
O motor agora calcula trajetórias curvas para o cursor. Isso evita que o WAF identifique o "salto" de coordenadas típico de automações.
> [!TIP]
> **Tática:** O robô faz "hovers" (passa o mouse) em posições aleatórias para simular leitura antes de extrair.

### 2. Adaptive Mimicry (Consciência de Container)
Diferente de scrapers comuns, o Cloner CLI detecta se está em uma SPA (como o Google Maps).
*   **Ação:** Se houver um `role="main"`, o comportamento biométrico é focado **dentro do painel**, garantindo que o scroll carregue os dados dinâmicos corretamente sem quebrar o layout global.

### 3. Protocolo Shadow (Persona SEO)
Para portais de notícias, mascaramos o tráfego como originado de uma busca orgânica.
*   **Header:** `Referer: https://www.google.com/search?q=...`
*   **User-Agent:** Google Persona ou Chrome Moderno.

---

## 🚨 Checklist de Integridade (Data Guard)

Antes de considerar uma extração como "Sucesso", o sistema agora valida:

| Check | Critério | Ação de Falha |
| :--- | :--- | :--- |
| **Volume de HTML** | `< 3.000 bytes` | Alerta de "Casca Vazia" + Retry |
| **Semantic Density** | `0 tokens` | Ativa sensor de block e log de erro |
| **JSON-LD Context** | `Presente?` | Usa como context de fallback se o DOM falhar |

---

## 📈 Próximos Passos de Evolução

Se você encontrar um site que ainda resiste ao **Ghost Cursor + Protocolo Shadow**, os próximos passos de grau militar são:
1.  **Proxies Residenciais:** Para evitar o bloqueio de IP.
2.  **Solvers de Captcha:** Integração com APIs como `2captcha` para resolver puzzles visuais.
3.  **Wait for Content:** Ajustar o `scraper.py` para esperar por seletores de conteúdo real (ex: `.article-body`) em vez de apenas o carregamento da página.

---
*Documento de Inteligência gerado por **Antigravity AI** para o projeto **Cloner CLI**.*
