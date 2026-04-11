# Layout System — Mobile Live Streaming App for Games, VTubers & More | PRISM Live Studio Mobile
> Gerado pelo Process Cloner em 11/04/2026 18:09
> **REGRA**: Toda nova seção deve respeitar este sistema de grid e breakpoints.

---

## Tecnologias de layout identificadas

- Flexbox

**Container max-width**: `100%`

```css
.container {
  max-width: 100%;
  margin: 0 auto;
  padding: 0 1.5rem;
}
```

## Breakpoints responsivos

| Breakpoint | Largura | Uso |
|------------|---------|-----|
| `1024px` | 1024px | Desktop |
| `1280px` | 1280px | Breakpoint |

### Template padrão de media queries

```css
@media (max-width: 1024px) {
  /* ajustes para Desktop */
}

@media (max-width: 1280px) {
  /* ajustes para 1280px */
}

```

## Padrões Flexbox

- `flex-direction: column`

## Estrutura de seções HTML

```html
<footer> .component-footer-21
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
    <!-- container max-width: 100% -->
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

*Process Cloner — 11/04/2026 18:09*