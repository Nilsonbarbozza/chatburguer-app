# Prompts para Claude Code — Face Effects · Filters · Stickers | PRISM Effects
> Gerado pelo Process Cloner em 11/04/2026 17:31
> Copie e cole estes prompts diretamente no Claude Code.
> Eles já referenciam os arquivos de skill corretos.

---

## Como usar

1. Abra o terminal na pasta `output/`
2. Execute: `claude`
3. Copie um dos prompts abaixo e cole

---

## Prompt 1 — Personalizar conteúdo mantendo o design

```
Leia os arquivos da pasta skills/ antes de qualquer alteração:
- skills/design-tokens.md → paleta de cores e tipografia
- skills/layout-system.md → grid e breakpoints
- skills/components.md → estrutura de cada componente
- skills/ux-patterns.md → animações e interações

Vou personalizar o projeto em output/index.html.
Regras obrigatórias:
- Preserve TODAS as cores: as cores do design-tokens.md
- Preserve a fonte: fonte documentada no design-tokens.md
- Mantenha o container com max-width: 1200px
- Mantenha o sistema de layout: layout padrão
- Os componentes existentes (Navbar, Botões / CTA, Footer, Alerta / Toast) devem continuar funcionando

Minha personalização:
[DESCREVA AQUI O QUE QUER MUDAR]
```

---

## Prompt 2 — Criar nova seção respeitando o design system

```
Leia skills/design-tokens.md e skills/components.md.

Crie uma nova seção HTML para inserir em output/index.html.
A seção deve seguir exatamente o design system do projeto:
- Usar apenas as cores de skills/design-tokens.md
- Usar a fonte fonte documentada no design-tokens.md
- Seguir o grid documentado em skills/layout-system.md
- Ter os mesmos padrões de hover/transição de skills/ux-patterns.md

A nova seção é:
[DESCREVA A SEÇÃO: ex. 'seção de FAQ com 5 perguntas sobre o produto']
```

---

## Prompt 3 — Corrigir responsividade

```
Leia skills/layout-system.md para ver os breakpoints do projeto.

Analise output/index.html e styles/styles.css.
Corrija os problemas de responsividade respeitando os breakpoints documentados.

Prioridade:
1. Mobile (768px ou menor)
2. Tablet
3. Desktop

Não altere cores, fontes nem estrutura de componentes.
```

---

## Prompt 4 — Adicionar interatividade JavaScript

```
Leia skills/ux-patterns.md para entender os padrões de interação do projeto.

Adicione a seguinte funcionalidade em scripts/main.js:
[DESCREVA A FUNCIONALIDADE: ex. 'menu mobile hamburguer que abre/fecha']

Regras:
- Use vanilla JS (sem jQuery ou frameworks)
- Siga as durações de transição documentadas em ux-patterns.md
- Adicione estados :hover e :focus conforme o padrão do projeto
- O código deve funcionar nos navegadores modernos
```

---

## Prompt 5 — Auditoria completa do projeto

```
Leia todos os arquivos da pasta skills/:
- skills/design-tokens.md
- skills/layout-system.md
- skills/components.md
- skills/ux-patterns.md

Depois analise output/index.html e styles/styles.css.

Faça uma auditoria e liste:
1. Inconsistências de cor (cores que não estão no design-tokens.md)
2. Problemas de responsividade
3. Componentes com HTML semântico incorreto
4. Estados de interação faltando (:hover, :focus)
5. Oportunidades de melhoria de performance CSS

Priorize por impacto visual no usuário.
```

---

## Prompt 6 — Preparar para produção

```
Leia skills/layout-system.md e skills/ux-patterns.md.

Prepare o projeto output/ para deploy em produção:
1. Valide o HTML semântico (tags corretas, alt em imagens, aria-labels)
2. Verifique se todas as imagens têm fallback
3. Confirme que o CSS não tem regras duplicadas
4. Valide responsividade nos breakpoints documentados
5. Adicione meta tags de SEO básico ao index.html
6. Confirme que scripts/main.js não tem erros de console

Não altere nenhum estilo visual — apenas qualidade e correção.
```

---

*Process Cloner — 11/04/2026 17:31*