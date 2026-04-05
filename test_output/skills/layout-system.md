# Layout System — Test Shadow Build
> Gerado pelo Process Cloner em 05/04/2026 10:43
> **REGRA**: Toda nova seção deve respeitar este sistema de grid e breakpoints.

---

## Tecnologias de layout identificadas

- Tailwind CSS

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
    <!-- container max-width: None -->
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

*Process Cloner — 05/04/2026 10:43*