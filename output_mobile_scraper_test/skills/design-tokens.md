# Design Tokens — Mobile Live Streaming App for Games, VTubers & More | PRISM Live Studio Mobile
> Gerado pelo Process Cloner em 11/04/2026 18:09
> **REGRA PRINCIPAL**: Nunca invente ou substitua estes valores.
> Toda cor, fonte e espaçamento do projeto deve vir exclusivamente deste arquivo.

---

## Paleta de cores

### Variáveis CSS (use estas em todo o código)

```css
:root {
  --brand-primary: #FFF;
  --brand-accent: #255DE4;
  --text-dark-4: #0B0B0B;
  --bg-light-5: #F9F9F9;
  --text-dark-6: #000;
  --color-palette-8: #222;
  --color-palette-9: #555;
  --color-palette-10: #1E1E1E;
  --color-palette-12: #D8D8D8;
  --color-palette-13: #343434;
  --text-dark-14: #007AFF;
  --color-palette-18: #AEAEAE;
  --color-palette-19: #CCC;
  --swiper-theme-color: var(--text-dark-14);
  --swiper-preloader-color: var(--text-dark-6);
}
```

### Uso semântico

- **primary**: `#FFFFFF`
- **text**: `#0B0B0B`

### Cores por frequência de uso

| # | Cor | Uso |
|---|-----|-----|
| 1 | `TRANSPARENT` | 42x no CSS |
| 2 | `#FFFFFF` | 29x no CSS |
| 3 | `#255DE4` | 22x no CSS |
| 4 | `#0B0B0B` | 15x no CSS |
| 5 | `#F9F9F9` | 15x no CSS |
| 6 | `#000000` | 13x no CSS |
| 7 | `#222222` | 6x no CSS |
| 8 | `#555555` | 6x no CSS |

## Tipografia

### Variáveis de fonte

```css
:root {
  --font-main: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, "Helvetica Neue", "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif;
}
```

### Famílias de fonte

- `var(--font-main)` — Principal
- `swiper-icons` — Display/Títulos
- `Helvetica` — Auxiliar

**Pesos utilizados**: `400`, `500`, `600`, `700`

## Espaçamentos e dimensões

### Variáveis de espaçamento

```css
:root {
  --swiper-navigation-size: 44px;
}
```

**Paddings mais usados**: `30px`, `55px`, `10px`, `20px`, `4px`, `282px 0 0 610px`

**Gaps (grid/flex)**: `0 8px`, `50px 60px`

**Border-radius**: `999px`, `10px`, `40px`

### Box shadows

```css
box-shadow: 1px 0 0 var(--text-dark-7), -1px 0 0 var(--text-dark-7), 0 1px 0 var(--text-dark-7), 0 -1px 0 var(--text-dark-7);
box-shadow: 1px 0 0 var(--text-dark-7), -1px 0 0 var(--text-dark-7), 0 1px 0 var(--text-dark-7), 0 -1px 0 var(--text-dark-7);
box-shadow: 0 0 10px 0 var(--text-dark-7);
```

---

*Process Cloner — 11/04/2026 18:09*