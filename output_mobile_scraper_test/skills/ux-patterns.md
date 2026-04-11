# UX Patterns — Mobile Live Streaming App for Games, VTubers & More | PRISM Live Studio Mobile
> Gerado pelo Process Cloner em 11/04/2026 18:09
> **REGRA**: Preserve estes comportamentos em todas as interações.
> Eles definem a personalidade e o feel do produto.

---

## Comportamento de scroll e navegação

- Scroll suave: `não detectado`
- Elementos sticky (navbar/sidebar): `não detectado`

## Animações (@keyframes)

- `@keyframes moving2`
- `@keyframes ani_moving`
- `@keyframes ani_09`
- `@keyframes change_opacity`
- `@keyframes change_opacity2`
- `@keyframes hide_up`

**Durações de animação detectadas**: `0.5s`, `0.7s`, `0.9s`, `55s`

## Transições CSS

```css
transition: transform 0.3s ease-in, background-color 0.3s linear, -webkit-transform 0.3s ease-in;
transition: 0.3s opacity;
transition: opacity;
transition: 0.2s transform, 0.2s left, 0.2s -webkit-transform;
transition: -webkit-transform;
```

## Estados :hover

```css
a:hover:hover {
  text-decoration: none;
}
```

```css
area .more_link:hover .go_arr .black_arr:hover {
  -webkit-transform: translate(50px, -50px);
  -ms-transform: translate(50px, -50px);
  transform: translate(50px, -50px);
}
```

```css
_area .more_link:hover .go_arr .blue_arr:hover {
  -webkit-transform: translate(0, -28px);
  -ms-transform: translate(0, -28px);
  transform: translate(0, -28px);
}
```

```css
nefit_list [class*=swiper-button-]:hover:hover {
  width: 50px;
  height: 50px;
  background-image: url(../images/css_asset_f76f2adb6b.png);
}
```

## Estados :focus (acessibilidade)

```css
.slick-list:focus:focus {
  outline: none;
}
```

```css
.slick-dots li:nth-child(1) button:focus:focus {
  width: 46px;
  height: 27px;
  background-image: url(../images/css_asset_d014840cd8.png);
}
```

```css
.slick-dots li:nth-child(2) button:focus:focus {
  width: 46px;
  height: 27px;
  background-image: url(../images/css_asset_e81f418657.png);
}
```

```css
.slick-dots li:nth-child(3) button:focus:focus {
  width: 46px;
  height: 27px;
  background-image: url(../images/css_asset_bfd13b2869.png);
}
```

## Eventos JavaScript identificados

Os seguintes eventos estão implementados no `scripts/main.js`:

- `click`
- `scroll`

Mantenha estes comportamentos ao refatorar o JavaScript.

## Diretrizes de UX para novas funcionalidades

Ao adicionar novos elementos, siga estas regras extraídas do design original:

1. **Consistência de interação** — use as mesmas durações de transição já definidas
2. **Feedback visual** — todo elemento clicável deve ter estado :hover documentado acima
3. **Acessibilidade** — mantenha estados :focus visíveis conforme padrão do projeto
4. **Mobile first** — valide o comportamento nos breakpoints documentados em `layout-system.md`

---

*Process Cloner — 11/04/2026 18:09*