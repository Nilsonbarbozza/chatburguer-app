# Layout System — Efeitos faciais · Filtros · Adesivos | PRISM Effects
> Gerado pelo Process Cloner em 11/04/2026 16:48
> **REGRA**: Toda nova seção deve respeitar este sistema de grid e breakpoints.

---

## Tecnologias de layout identificadas

- Flexbox
- CSS Grid

**Container max-width**: `380px`

```css
.container {
  max-width: 380px;
  margin: 0 auto;
  padding: 0 1.5rem;
}
```

## Grid columns identificados

```css
grid-template-columns: 1fr 1fr;
```

```css
grid-template-columns: 2fr 6fr;
```

## Padrões Flexbox

- `flex-direction: row`
- `flex-direction: column`

## Estrutura de seções HTML

```html
<footer> .footer
```

## Template base de nova página

Use esta estrutura ao criar qualquer nova página:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Página</title>
  <link rel="stylesheet" href="../styles/styles.css">
</head>
<body>
  <!-- HEADER -->
  <header><!-- navbar aqui --></header>

  <!-- MAIN -->
  <main>
    <!-- container max-width: 380px -->
    <div class="container">
      <!-- conteúdo aqui -->
    </div>
  </main>

  <!-- FOOTER -->
  <footer><!-- footer aqui --></footer>
  <script src="../scripts/main.js" defer></script>
</body>
</html>
```

---

*Process Cloner — 11/04/2026 16:48*