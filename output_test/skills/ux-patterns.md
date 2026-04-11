# UX Patterns — Efeitos faciais · Filtros · Adesivos | PRISM Effects
> Gerado pelo Process Cloner em 11/04/2026 16:48
> **REGRA**: Preserve estes comportamentos em todas as interações.
> Eles definem a personalidade e o feel do produto.

---

## Comportamento de scroll e navegação

- Scroll suave: `não detectado`
- Elementos sticky (navbar/sidebar): `sim`

## Animações (@keyframes)

- `@keyframes ani_moving`
- `@keyframes spinner-dash`
- `@keyframes change_opacity2`
- `@keyframes spin`
- `@keyframes ani_03`
- `@keyframes show_up`

**Durações de animação detectadas**: `1.25s`, `0.35s`, `1.75s`, `0.25s`

## Transições CSS

```css
transition: transform;
transition: opacity 0.24s ease-out;
transition: color 0.3s;
transition: transform 0.6s;
transition: linear;
```

## Estados :hover

```css
area .more_link:hover .go_arr .black_arr:hover {
  transition: transform 0.35s ease-out;
  transform: translate(50px, -50px);
}
```

```css
_area .more_link:hover .go_arr .blue_arr:hover {
  transition: transform 0.35s ease-out;
  transform: translate(0, -28px);
}
```

```css
fit_list [class*="swiper-button-"]:hover:hover {
  background-image: var(--sf-img-126);
  background-position: -55px -477px;
  background-repeat: no-repeat;
}
```

```css
header .menu_list > li:hover > a .title3:hover {
  font-weight: 700;
}
```

## Estados :focus (acessibilidade)

```css
.slick-list:focus:focus {
  outline: none;
}
```

```css
 .slick-dots li:first-child button:focus:focus {
  background-image: var(--sf-img-126);
  background-position: -601px -32px;
  background-repeat: no-repeat;
}
```

```css
.slick-dots li:nth-child(2) button:focus:focus {
  background-image: var(--sf-img-126);
  background-position: -601px -160px;
  background-repeat: no-repeat;
}
```

```css
.slick-dots li:nth-child(3) button:focus:focus {
  background-image: var(--sf-img-126);
  background-position: -601px -288px;
  background-repeat: no-repeat;
}
```

## Diretrizes de UX para novas funcionalidades

Ao adicionar novos elementos, siga estas regras extraídas do design original:

1. **Consistência de interação** — use as mesmas durações de transição já definidas
2. **Feedback visual** — todo elemento clicável deve ter estado :hover documentado acima
3. **Acessibilidade** — mantenha estados :focus visíveis conforme padrão do projeto
4. **Mobile first** — valide o comportamento nos breakpoints documentados em `layout-system.md`

---

*Process Cloner — 11/04/2026 16:48*