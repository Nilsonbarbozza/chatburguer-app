"""
core/skill_generator.py  v2
Stage 11 — Gerador de 5 arquivos de skill especializados para Claude Code

Arquivos gerados em skills/:
  design-tokens.md   → DNA visual: cores, tipografia, espaçamentos
  layout-system.md   → grid, breakpoints, estrutura de seções
  components.md      → catálogo HTML+CSS de cada componente identificado
  ux-patterns.md     → animações, hover states, comportamento interativo
  claude-prompts.md  → prompts prontos para usar no Claude Code
"""
import os
import re
import logging
from pathlib import Path
from typing  import Dict, Any, List, Optional, Tuple
from datetime import datetime

from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage
from core.config   import get_paths
from core.utils    import save_file, setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


# ══════════════════════════════════════════════════════════════
# STAGE
# ══════════════════════════════════════════════════════════════

class SkillGeneratorStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 11: Gerando 5 skills para Claude Code ===")
        paths = get_paths()
        os.makedirs(paths['SKILLS_DIR'], exist_ok=True)

        soup      = context.get('soup')
        css_text  = _read(paths['STYLE_FILE'])
        html_text = _read(os.path.join(paths['OUT_DIR'], 'index.html'))
        images_dir = paths['IMAGES_DIR']
        js_bundle  = context.get('js_bundle', '')

        analyzer = DesignAnalyzer(soup, css_text, html_text, images_dir, js_bundle)
        dna      = analyzer.extract()
        now      = datetime.now().strftime('%d/%m/%Y %H:%M')
        title    = dna['meta'].get('title') or 'Projeto Web'

        files = {
            'design-tokens.md':  _build_design_tokens(dna, title, now),
            'layout-system.md':  _build_layout_system(dna, title, now),
            'components.md':     _build_components(dna, title, now),
            'ux-patterns.md':    _build_ux_patterns(dna, title, now),
            'claude-prompts.md': _build_claude_prompts(dna, title, now, paths),
        }

        skill_files = []
        for filename, content in files.items():
            path = os.path.join(paths['SKILLS_DIR'], filename)
            save_file(path, content)
            skill_files.append(path)
            logger.info(f"  skill gerado: {path}")

        context['skill_files'] = skill_files
        context['skill_file']  = skill_files[-1]   # claude-prompts.md como principal
        return context


# ══════════════════════════════════════════════════════════════
# ANALYZER — extrai o DNA visual completo
# ══════════════════════════════════════════════════════════════

class DesignAnalyzer:
    def __init__(self, soup, css, html, images_dir, js_bundle=''):
        self.soup       = soup
        self.css        = css or ''
        self.html       = html or ''
        self.images_dir = images_dir
        self.js         = js_bundle or ''

    def extract(self) -> dict:
        return {
            'meta':        self._meta(),
            'colors':      self._colors(),
            'typography':  self._typography(),
            'spacing':     self._spacing(),
            'layout':      self._layout(),
            'components':  self._components(),
            'animations':  self._animations(),
            'interactions':self._interactions(),
            'images':      self._images(),
            'css_vars':    self._css_vars(),
        }

    # ── Meta ──────────────────────────────────────────────────
    def _meta(self) -> dict:
        m = {'title': '', 'description': '', 'lang': 'pt'}
        if not self.soup: return m
        if self.soup.title:
            m['title'] = (self.soup.title.string or '').strip()
        desc = self.soup.find('meta', attrs={'name': 'description'})
        if desc: m['description'] = desc.get('content', '')
        html_tag = self.soup.find('html')
        if html_tag: m['lang'] = html_tag.get('lang', 'pt')
        return m

    # ── Cores ─────────────────────────────────────────────────
    def _colors(self) -> dict:
        # Frequência de cores hex
        all_hex = re.findall(r'#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b', self.css)
        normalized = []
        for c in all_hex:
            if len(c) == 4:
                c = '#' + ''.join(x*2 for x in c[1:])
            normalized.append(c.upper())

        freq = {}
        for c in normalized:
            freq[c] = freq.get(c, 0) + 1
        top = sorted(freq, key=freq.get, reverse=True)

        # Tenta classificar por uso semântico
        semantic = {}
        sem_patterns = [
            ('primary',    r'(?:primary|main|brand|accent)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
            ('background', r'(?:background|bg)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
            ('text',       r'(?:color|text)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
            ('border',     r'(?:border)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
            ('success',    r'(?:success|green)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
            ('error',      r'(?:error|danger|red)[^:]*:\s*(#[0-9a-fA-F]{3,6})'),
        ]
        for label, pattern in sem_patterns:
            m = re.search(pattern, self.css, re.IGNORECASE)
            if m:
                c = m.group(1).upper()
                if len(c) == 4:
                    c = '#' + ''.join(x*2 for x in c[1:])
                semantic[label] = c

        return {'top': top[:12], 'semantic': semantic, 'freq': freq}

    # ── Tipografia ────────────────────────────────────────────
    def _typography(self) -> dict:
        families = {}
        for f in re.findall(r'font-family\s*:\s*([^;}{]+)', self.css, re.IGNORECASE):
            first = f.strip().split(',')[0].strip().strip('"\'')
            if first and len(first) > 1 and first.lower() not in ('inherit','initial','sans-serif','serif','monospace'):
                families[first] = families.get(first, 0) + 1
        sorted_families = sorted(families, key=families.get, reverse=True)

        sizes  = re.findall(r'font-size\s*:\s*([\d.]+(?:px|rem|em))', self.css, re.IGNORECASE)
        weights = re.findall(r'font-weight\s*:\s*(\d{3}|bold|normal)', self.css, re.IGNORECASE)
        heights = re.findall(r'line-height\s*:\s*([\d.]+(?:px|rem|em|)?)', self.css, re.IGNORECASE)

        # Hierarquia tipográfica — tamanhos usados em h1..h6
        hierarchy = {}
        for tag in ['h1','h2','h3','h4','h5','h6','p','small']:
            pattern = rf'{tag}\s*[,{{][^}}]*font-size\s*:\s*([\d.]+(?:px|rem|em))'
            m = re.search(pattern, self.css, re.IGNORECASE)
            if m:
                hierarchy[tag] = m.group(1)

        # Google Fonts
        google = re.findall(r'@import[^;]*fonts\.googleapis\.com[^;]+;', self.css)

        return {
            'families':  sorted_families[:4],
            'sizes':     sorted(set(sizes), key=lambda x: float(re.sub(r'[^\d.]','',x) or '0'))[:8],
            'weights':   sorted(set(weights))[:5],
            'heights':   list(set(heights))[:4],
            'hierarchy': hierarchy,
            'google':    google[:2],
        }

    # ── Espaçamentos ──────────────────────────────────────────
    def _spacing(self) -> dict:
        paddings = re.findall(r'padding(?:-(?:top|bottom|left|right))?\s*:\s*([\d.]+px)', self.css)
        margins  = re.findall(r'margin(?:-(?:top|bottom|left|right))?\s*:\s*([\d.]+px)', self.css)
        gaps     = re.findall(r'gap\s*:\s*([\d.]+px)', self.css)

        def top_values(vals, n=6):
            freq = {}
            for v in vals:
                freq[v] = freq.get(v, 0) + 1
            return sorted(freq, key=freq.get, reverse=True)[:n]

        # Border radius
        radii = re.findall(r'border-radius\s*:\s*([\d.]+px)', self.css)
        radius_freq = {}
        for r in radii:
            radius_freq[r] = radius_freq.get(r, 0) + 1
        top_radii = sorted(radius_freq, key=radius_freq.get, reverse=True)[:3]

        # Box shadows
        shadows = re.findall(r'box-shadow\s*:\s*([^;}]+)', self.css)

        return {
            'paddings':      top_values(paddings),
            'margins':       top_values(margins),
            'gaps':          top_values(gaps),
            'border_radius': top_radii,
            'shadows':       [s.strip() for s in shadows[:3]],
        }

    # ── Layout ────────────────────────────────────────────────
    def _layout(self) -> dict:
        css = self.css.replace(' ', '')
        layout = {
            'flexbox':   'display:flex' in css,
            'grid':      'display:grid' in css,
            'bootstrap': bool(re.search(r'bootstrap', self.css, re.I) or
                           (self.soup and self.soup.find(class_=re.compile(r'\bcol-\w+\b')))),
            'tailwind':  bool(re.search(r'tailwind', self.css, re.I)),
            'responsive': '@media' in self.css,
        }

        # Breakpoints
        breakpoints = re.findall(r'@media[^{]*\((?:max|min)-width\s*:\s*([\d.]+px)\)', self.css)
        layout['breakpoints'] = sorted(set(breakpoints),
                                       key=lambda x: int(re.sub(r'[^\d]','',x)))[:5]

        # Max-width do container
        max_widths = re.findall(r'max-width\s*:\s*([\d.]+(?:px|rem|%))', self.css)
        layout['max_width'] = max_widths[0] if max_widths else None

        # Grid columns
        grid_cols = re.findall(r'grid-template-columns\s*:\s*([^;]+);', self.css)
        layout['grid_columns'] = [g.strip() for g in grid_cols[:3]]

        # Flex patterns
        flex_dirs = re.findall(r'flex-direction\s*:\s*(row|column)', self.css)
        layout['flex_directions'] = list(set(flex_dirs))

        # Sections structure
        sections = []
        if self.soup:
            for tag in ['header','nav','section','main','article','aside','footer']:
                for el in self.soup.find_all(tag):
                    cls = ' '.join(el.get('class', []))[:50]
                    eid = el.get('id', '')
                    label = f'<{tag}>'
                    if eid: label += f' #{eid}'
                    elif cls: label += f' .{cls.split()[0]}'
                    sections.append(label)
        layout['sections'] = sections[:15]

        return layout

    # ── Componentes ───────────────────────────────────────────
    def _components(self) -> List[dict]:
        if not self.soup: return []
        found = []

        specs = [
            # (nome, detector, extrator_html)
            ('Navbar',        self._detect_navbar,    self._extract_navbar),
            ('Hero section',  self._detect_hero,      self._extract_hero),
            ('Botões / CTA',  self._detect_buttons,   self._extract_buttons),
            ('Cards',         self._detect_cards,     self._extract_cards),
            ('Formulário',    self._detect_form,      self._extract_form),
            ('Footer',        self._detect_footer,    self._extract_footer),
            ('Modal / Dialog',self._detect_modal,     self._extract_modal),
            ('Navegação tabs',self._detect_tabs,      self._extract_tabs),
            ('Accordion',     self._detect_accordion, self._extract_accordion),
            ('Seção de preços',self._detect_pricing,  self._extract_pricing),
            ('Depoimentos',   self._detect_testimonials, self._extract_testimonials),
            ('Grid de imagens',self._detect_gallery,  self._extract_gallery),
            ('Badges / Tags', self._detect_badges,    self._extract_badges),
            ('Alerta / Toast',self._detect_alerts,    self._extract_alerts),
        ]

        for name, detector, extractor in specs:
            try:
                element = detector()
                if element:
                    html_struct, css_classes = extractor(element)
                    found.append({
                        'name':      name,
                        'html':      html_struct,
                        'classes':   css_classes,
                        'tag':       element.name if hasattr(element, 'name') else '',
                    })
            except Exception:
                pass

        return found

    # Detectores
    def _detect_navbar(self):
        return (self.soup.find('nav') or
                self.soup.find(attrs={'role':'navigation'}) or
                self.soup.find(class_=re.compile(r'\b(?:navbar|nav-bar|header-nav)\b', re.I)))

    def _detect_hero(self):
        return (self.soup.find(class_=re.compile(r'\bhero\b|\bjumbotron\b|\bbanner\b', re.I)) or
                self.soup.find('section', class_=re.compile(r'intro|welcome|main-banner', re.I)))

    def _detect_buttons(self):
        return (self.soup.find(class_=re.compile(r'\bbtn\b|\bbutton\b|\bcta\b', re.I)) or
                self.soup.find('button') or self.soup.find('a', class_=re.compile(r'btn', re.I)))

    def _detect_cards(self):
        return self.soup.find(class_=re.compile(r'\bcard\b', re.I))

    def _detect_form(self):
        return self.soup.find('form')

    def _detect_footer(self):
        return self.soup.find('footer') or self.soup.find(class_=re.compile(r'\bfooter\b', re.I))

    def _detect_modal(self):
        return self.soup.find(class_=re.compile(r'\bmodal\b|\bdialog\b|\bpopup\b', re.I))

    def _detect_tabs(self):
        return self.soup.find(class_=re.compile(r'\btabs?\b|\btab-nav\b', re.I))

    def _detect_accordion(self):
        return self.soup.find(class_=re.compile(r'\baccordion\b|\bcollapse\b', re.I))

    def _detect_pricing(self):
        return self.soup.find(class_=re.compile(r'\bpricing\b|\bplano\b|\bplan\b', re.I))

    def _detect_testimonials(self):
        return self.soup.find(class_=re.compile(r'\btestimonial\b|\breview\b|\bdepoimento\b', re.I))

    def _detect_gallery(self):
        imgs = self.soup.find_all('img') if self.soup else []
        parent = None
        for img in imgs:
            p = img.parent
            if p and len(p.find_all('img')) >= 3:
                parent = p; break
        return parent

    def _detect_badges(self):
        return self.soup.find(class_=re.compile(r'\bbadge\b|\btag\b|\bchip\b|\bpill\b', re.I))

    def _detect_alerts(self):
        return self.soup.find(class_=re.compile(r'\balert\b|\btoast\b|\bnotification\b', re.I))

    # Extratores — retorna (html_simplificado, lista_de_classes)
    def _extract_navbar(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        links   = el.find_all('a', limit=5)
        items   = '\n    '.join(f'<li><a href="#">{(a.get_text(strip=True) or "Link")[:20]}</a></li>' for a in links)
        html = f'''<{el.name} class="{' '.join(el.get('class', []))[:80]}">
  <div class="nav-brand">Logo</div>
  <ul class="nav-links">
    {items or '<li><a href="#">Link</a></li>'}
  </ul>
</{el.name}>'''
        return html, classes

    def _extract_hero(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        h1 = el.find(['h1','h2'])
        p  = el.find('p')
        btn = el.find(class_=re.compile(r'btn', re.I)) or el.find('button') or el.find('a')
        html = f'''<section class="{' '.join(el.get('class', []))[:80]}">
  <h1>{(h1.get_text(strip=True) if h1 else 'Título Principal')[:60]}</h1>
  <p>{(p.get_text(strip=True) if p else 'Subtítulo descritivo da proposta de valor.')[:100]}</p>
  {f'<a class="{" ".join(btn.get("class", []))[:40]}" href="#">Chamada para ação</a>' if btn else '<a class="btn-primary" href="#">Começar agora</a>'}
</section>'''
        return html, classes

    def _extract_buttons(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        # Coleta variações de botão
        all_btns = self.soup.find_all(class_=re.compile(r'\bbtn\b', re.I), limit=6)
        unique_classes = list({' '.join(b.get('class',[])) for b in all_btns})[:4]
        lines = [f'<button class="{c[:60]}">Rótulo</button>' for c in unique_classes]
        html = '\n'.join(lines) or f'<button class="{" ".join(el.get("class",[]))[:60]}">Rótulo</button>'
        return html, classes

    def _extract_cards(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        img  = el.find('img')
        h    = el.find(['h2','h3','h4'])
        p    = el.find('p')
        link = el.find('a')
        html = f'''<div class="{' '.join(el.get('class', []))[:80]}">
  {f'<img src="images/placeholder.jpg" alt="imagem">' if img else ''}
  <div class="card-body">
    <h3>{(h.get_text(strip=True) if h else 'Título do card')[:50]}</h3>
    <p>{(p.get_text(strip=True) if p else 'Descrição do conteúdo do card.')[:100]}</p>
    {f'<a class="{" ".join(link.get("class",[]))[:40]}" href="#">Ver mais</a>' if link else ''}
  </div>
</div>'''
        return html, classes

    def _extract_form(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        inputs  = el.find_all('input', limit=4)
        textarea = el.find('textarea')
        btn      = el.find(['button', 'input[type=submit]'])
        lines = []
        for inp in inputs:
            t = inp.get('type','text')
            if t in ('submit','button','hidden'): continue
            ph = inp.get('placeholder', inp.get('name', t))[:30]
            lines.append(f'  <input type="{t}" placeholder="{ph}">')
        if textarea:
            lines.append(f'  <textarea placeholder="{textarea.get("placeholder","Mensagem")[:30]}"></textarea>')
        lines.append(f'  <button type="submit" class="{" ".join((btn.get("class",[]) if btn else []))[:40]}">Enviar</button>')
        html = f'<form class="{" ".join(el.get("class",[]))[:60]}">\n' + '\n'.join(lines) + '\n</form>'
        return html, classes

    def _extract_footer(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        cols    = el.find_all(class_=re.compile(r'col|column|footer-col', re.I), limit=4)
        n_cols  = max(len(cols), 1)
        html = f'<footer class="{" ".join(el.get("class",[]))[:60]}">\n'
        html += f'  <div class="footer-grid" style="grid-template-columns: repeat({n_cols}, 1fr);">\n'
        for i in range(n_cols):
            html += f'    <div class="footer-col"><h4>Coluna {i+1}</h4><ul><li><a href="#">Link</a></li></ul></div>\n'
        html += '  </div>\n  <p class="footer-copy">&copy; 2025 Empresa</p>\n</footer>'
        return html, classes

    def _extract_modal(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'''<div class="{' '.join(el.get('class', []))[:60]}" role="dialog" aria-modal="true">
  <div class="modal-header">
    <h3>Título do modal</h3>
    <button class="modal-close" aria-label="Fechar">&times;</button>
  </div>
  <div class="modal-body">Conteúdo do modal.</div>
  <div class="modal-footer">
    <button class="btn-secondary">Cancelar</button>
    <button class="btn-primary">Confirmar</button>
  </div>
</div>'''
        return html, classes

    def _extract_tabs(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        items   = el.find_all(['li','button','a'], limit=4)
        labels  = [i.get_text(strip=True)[:20] or f'Tab {n}' for n, i in enumerate(items, 1)]
        nav = '  '.join(f'<button class="tab-btn" data-tab="{i}">{l}</button>' for i, l in enumerate(labels))
        html = f'<div class="{" ".join(el.get("class",[]))[:60]}">\n  <nav class="tab-nav">{nav}</nav>\n  <div class="tab-content">Conteúdo da aba ativa.</div>\n</div>'
        return html, classes

    def _extract_accordion(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'''<div class="{' '.join(el.get('class', []))[:60]}">
  <div class="accordion-item">
    <button class="accordion-header">Pergunta 1</button>
    <div class="accordion-body">Resposta da pergunta 1.</div>
  </div>
  <div class="accordion-item">
    <button class="accordion-header">Pergunta 2</button>
    <div class="accordion-body">Resposta da pergunta 2.</div>
  </div>
</div>'''
        return html, classes

    def _extract_pricing(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'''<section class="{' '.join(el.get('class', []))[:60]}">
  <div class="pricing-grid">
    <div class="pricing-card">
      <h3>Básico</h3>
      <p class="price">R$ 0/mês</p>
      <ul><li>Feature 1</li><li>Feature 2</li></ul>
      <a class="btn-outline" href="#">Começar</a>
    </div>
    <div class="pricing-card pricing-featured">
      <h3>Pro</h3>
      <p class="price">R$ 49/mês</p>
      <ul><li>Tudo do Básico</li><li>Feature Pro</li></ul>
      <a class="btn-primary" href="#">Assinar</a>
    </div>
  </div>
</section>'''
        return html, classes

    def _extract_testimonials(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'''<section class="{' '.join(el.get('class', []))[:60]}">
  <div class="testimonials-grid">
    <blockquote class="testimonial-card">
      <p>"Depoimento do cliente sobre o produto."</p>
      <footer><cite>Nome do Cliente — Cargo</cite></footer>
    </blockquote>
  </div>
</section>'''
        return html, classes

    def _extract_gallery(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'''<div class="{' '.join(el.get('class', []))[:60]}">
  <img src="images/img_1.jpg" alt="Imagem 1">
  <img src="images/img_2.jpg" alt="Imagem 2">
  <img src="images/img_3.jpg" alt="Imagem 3">
</div>'''
        return html, classes

    def _extract_badges(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'<span class="{" ".join(el.get("class",[]))[:60]}">Rótulo</span>'
        return html, classes

    def _extract_alerts(self, el) -> Tuple[str, List[str]]:
        classes = _top_classes(el)
        html = f'<div class="{" ".join(el.get("class",[]))[:60]}" role="alert">Mensagem de alerta.</div>'
        return html, classes

    # ── Animações ─────────────────────────────────────────────
    def _animations(self) -> dict:
        keyframes = re.findall(r'@keyframes\s+([\w-]+)', self.css)
        transitions = re.findall(r'transition\s*:\s*([^;}{]+)', self.css)
        transforms  = re.findall(r'transform\s*:\s*([^;}{]+)', self.css)
        durations   = re.findall(r'(?:transition|animation)[^:]*:\s*[^;]*?([\d.]+s)\b', self.css)
        return {
            'keyframes':   list(set(keyframes))[:6],
            'transitions': [t.strip() for t in set(transitions)][:5],
            'transforms':  [t.strip() for t in set(transforms)][:5],
            'durations':   list(set(durations))[:4],
        }

    # ── Interações ────────────────────────────────────────────
    def _interactions(self) -> dict:
        hover_rules  = re.findall(r'([^{}]+):hover\s*\{([^}]+)\}', self.css)
        focus_rules  = re.findall(r'([^{}]+):focus\s*\{([^}]+)\}', self.css)
        active_rules = re.findall(r'([^{}]+):active\s*\{([^}]+)\}', self.css)

        def simplify(rules, limit=4):
            out = []
            for selector, props in rules[:limit]:
                sel = selector.strip()[-40:]
                prop_list = [p.strip() for p in props.split(';') if p.strip()][:3]
                out.append({'selector': sel, 'properties': prop_list})
            return out

        # Scroll behavior
        scroll = 'scroll-behavior' in self.css
        sticky = 'position:sticky' in self.css.replace(' ','') or 'position: sticky' in self.css

        # JS interactions
        js_events = []
        for evt in ['click','scroll','mouseover','keydown','submit','change','input']:
            if evt in self.js:
                js_events.append(evt)

        return {
            'hover':         simplify(hover_rules),
            'focus':         simplify(focus_rules),
            'active':        simplify(active_rules),
            'smooth_scroll': scroll,
            'sticky':        sticky,
            'js_events':     js_events,
        }

    # ── Imagens ───────────────────────────────────────────────
    def _images(self) -> dict:
        count = 0
        types = {}
        if os.path.isdir(self.images_dir):
            for f in Path(self.images_dir).iterdir():
                if f.is_file():
                    count += 1
                    ext = f.suffix.lower()
                    types[ext] = types.get(ext, 0) + 1
        return {'total': count, 'by_type': types}

    # ── CSS custom properties ─────────────────────────────────
    def _css_vars(self) -> dict:
        vars_found = re.findall(r'(--[\w-]+)\s*:\s*([^;}{]+);', self.css)
        result = {}
        for name, val in vars_found:
            result[name.strip()] = val.strip()
        return result


# ══════════════════════════════════════════════════════════════
# BUILDERS — gera cada arquivo de skill
# ══════════════════════════════════════════════════════════════

def _build_design_tokens(dna: dict, title: str, now: str) -> str:
    colors   = dna['colors']
    typo     = dna['typography']
    spacing  = dna['spacing']
    css_vars = dna['css_vars']

    L = [
        f"# Design Tokens — {title}",
        f"> Gerado pelo Process Cloner em {now}",
        f"> **REGRA PRINCIPAL**: Nunca invente ou substitua estes valores.",
        f"> Toda cor, fonte e espaçamento do projeto deve vir exclusivamente deste arquivo.",
        "",
        "---",
        "",
        "## Paleta de cores",
        "",
    ]

    # Variáveis CSS de cor
    color_vars = {k: v for k, v in css_vars.items()
                  if any(w in k for w in ['color','bg','background','primary','secondary','accent','text','border','surface'])}
    if color_vars:
        L += ["### Variáveis CSS (use estas em todo o código)", "", "```css", ":root {"]
        for k, v in list(color_vars.items())[:20]:
            L.append(f"  {k}: {v};")
        L += ["}", "```", ""]

    # Semântica de cores
    if colors['semantic']:
        L.append("### Uso semântico")
        L.append("")
        for role, hex_val in colors['semantic'].items():
            L.append(f"- **{role}**: `{hex_val}`")
        L.append("")

    # Top cores por frequência
    if colors['top']:
        L.append("### Cores por frequência de uso")
        L.append("")
        L.append("| # | Cor | Uso |")
        L.append("|---|-----|-----|")
        for i, c in enumerate(colors['top'][:8], 1):
            freq = colors['freq'].get(c, 0)
            L.append(f"| {i} | `{c}` | {freq}x no CSS |")
        L.append("")

    # Tipografia
    L += ["## Tipografia", ""]

    typo_vars = {k: v for k, v in css_vars.items() if 'font' in k or 'type' in k}
    if typo_vars:
        L += ["### Variáveis de fonte", "", "```css", ":root {"]
        for k, v in typo_vars.items():
            L.append(f"  {k}: {v};")
        L += ["}", "```", ""]

    if typo['families']:
        L.append("### Famílias de fonte")
        L.append("")
        for i, f in enumerate(typo['families'], 1):
            role = "Principal" if i == 1 else ("Display/Títulos" if i == 2 else "Auxiliar")
            L.append(f"- `{f}` — {role}")
        L.append("")

    if typo['google']:
        L.append("### Import Google Fonts (adicionar ao `<head>`)")
        L.append("")
        L.append("```css")
        for gf in typo['google']:
            L.append(gf)
        L.append("```")
        L.append("")

    if typo['hierarchy']:
        L.append("### Hierarquia tipográfica")
        L.append("")
        L.append("```css")
        for tag, size in typo['hierarchy'].items():
            L.append(f"{tag} {{ font-size: {size}; }}")
        L.append("```")
        L.append("")

    if typo['weights']:
        L.append(f"**Pesos utilizados**: {', '.join(f'`{w}`' for w in typo['weights'])}")
        L.append("")

    # Espaçamentos
    L += ["## Espaçamentos e dimensões", ""]

    spacing_vars = {k: v for k, v in css_vars.items()
                    if any(w in k for w in ['space','gap','padding','margin','size','radius'])}
    if spacing_vars:
        L += ["### Variáveis de espaçamento", "", "```css", ":root {"]
        for k, v in list(spacing_vars.items())[:12]:
            L.append(f"  {k}: {v};")
        L += ["}", "```", ""]

    if spacing['paddings']:
        L.append(f"**Paddings mais usados**: {', '.join(f'`{p}`' for p in spacing['paddings'])}")
        L.append("")
    if spacing['gaps']:
        L.append(f"**Gaps (grid/flex)**: {', '.join(f'`{g}`' for g in spacing['gaps'])}")
        L.append("")
    if spacing['border_radius']:
        L.append(f"**Border-radius**: {', '.join(f'`{r}`' for r in spacing['border_radius'])}")
        L.append("")
    if spacing['shadows']:
        L.append("### Box shadows")
        L.append("")
        L.append("```css")
        for s in spacing['shadows']:
            L.append(f"box-shadow: {s};")
        L.append("```")
        L.append("")

    L += ["---", "", f"*Process Cloner — {now}*"]
    return '\n'.join(L)


def _build_layout_system(dna: dict, title: str, now: str) -> str:
    layout = dna['layout']
    L = [
        f"# Layout System — {title}",
        f"> Gerado pelo Process Cloner em {now}",
        f"> **REGRA**: Toda nova seção deve respeitar este sistema de grid e breakpoints.",
        "",
        "---",
        "",
        "## Tecnologias de layout identificadas",
        "",
    ]

    techs = []
    if layout['flexbox']:   techs.append("Flexbox")
    if layout['grid']:      techs.append("CSS Grid")
    if layout['bootstrap']: techs.append("Bootstrap")
    if layout['tailwind']:  techs.append("Tailwind CSS")
    for t in techs:
        L.append(f"- {t}")
    L.append("")

    if layout['max_width']:
        L.append(f"**Container max-width**: `{layout['max_width']}`")
        L.append("")
        L += [
            "```css",
            ".container {",
            f"  max-width: {layout['max_width']};",
            "  margin: 0 auto;",
            "  padding: 0 1.5rem;",
            "}",
            "```",
            "",
        ]

    if layout['breakpoints']:
        L += ["## Breakpoints responsivos", ""]
        L.append("| Breakpoint | Largura | Uso |")
        L.append("|------------|---------|-----|")
        bp_labels = {
            '480px': 'Mobile pequeno', '576px': 'Mobile',
            '768px': 'Tablet', '992px': 'Desktop médio',
            '1024px': 'Desktop', '1200px': 'Desktop grande',
            '1440px': 'Wide', '1536px': 'Ultra wide',
        }
        for bp in layout['breakpoints']:
            label = bp_labels.get(bp, 'Breakpoint')
            L.append(f"| `{bp}` | {bp} | {label} |")
        L.append("")

        # Template de media query
        L += [
            "### Template padrão de media queries",
            "",
            "```css",
        ]
        for bp in layout['breakpoints'][:3]:
            L.append(f"@media (max-width: {bp}) {{")
            L.append(f"  /* ajustes para {bp_labels.get(bp, bp)} */")
            L.append("}")
            L.append("")
        L.append("```")
        L.append("")

    if layout['grid_columns']:
        L += ["## Grid columns identificados", ""]
        for gc in layout['grid_columns']:
            L += ["```css", f"grid-template-columns: {gc};", "```", ""]

    if layout['flex_directions']:
        L += ["## Padrões Flexbox", ""]
        for fd in layout['flex_directions']:
            L.append(f"- `flex-direction: {fd}`")
        L.append("")

    if layout['sections']:
        L += ["## Estrutura de seções HTML", "", "```html"]
        for s in layout['sections']:
            L.append(s)
        L += ["```", ""]

    # Template de nova página
    L += [
        "## Template base de nova página",
        "",
        "Use esta estrutura ao criar qualquer nova página:",
        "",
        "```html",
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        "<head>",
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>Página</title>',
        '  <link rel="stylesheet" href="../styles/styles.css">',
        "</head>",
        "<body>",
        "  <!-- HEADER -->",
        "  <header><!-- navbar aqui --></header>",
        "",
        "  <!-- MAIN -->",
        "  <main>",
        f"    <!-- container max-width: {layout.get('max_width','1200px')} -->",
        '    <div class="container">',
        "      <!-- conteúdo aqui -->",
        "    </div>",
        "  </main>",
        "",
        "  <!-- FOOTER -->",
        "  <footer><!-- footer aqui --></footer>",
        '  <script src="../scripts/main.js" defer></script>',
        "</body>",
        "</html>",
        "```",
        "",
        "---",
        "",
        f"*Process Cloner — {now}*",
    ]
    return '\n'.join(L)


def _build_components(dna: dict, title: str, now: str) -> str:
    components = dna['components']
    L = [
        f"# Catálogo de Componentes — {title}",
        f"> Gerado pelo Process Cloner em {now}",
        f"> **REGRA**: Ao criar um componente existente neste catálogo, use",
        f"> exatamente as classes CSS documentadas. Não invente nomes de classe.",
        "",
        "---",
        "",
    ]

    if not components:
        L.append("Nenhum componente identificado automaticamente.")
        L.append("Analise o `index.html` e o `styles/styles.css` para identificá-los.")
    else:
        L.append(f"**{len(components)} componentes identificados:**")
        L.append("")
        for c in components:
            L.append(f"- {c['name']}")
        L.append("")
        L.append("---")
        L.append("")

        for comp in components:
            L.append(f"## {comp['name']}")
            L.append("")

            if comp['classes']:
                L.append("**Classes CSS principais:**")
                L.append("")
                for cls in comp['classes']:
                    L.append(f"- `.{cls}`")
                L.append("")

            if comp['html']:
                L.append("**Estrutura HTML:**")
                L.append("")
                L.append("```html")
                L.append(comp['html'])
                L.append("```")
                L.append("")

            L.append("---")
            L.append("")

    L += [f"*Process Cloner — {now}*"]
    return '\n'.join(L)


def _build_ux_patterns(dna: dict, title: str, now: str) -> str:
    anim   = dna['animations']
    inter  = dna['interactions']
    layout = dna['layout']
    L = [
        f"# UX Patterns — {title}",
        f"> Gerado pelo Process Cloner em {now}",
        f"> **REGRA**: Preserve estes comportamentos em todas as interações.",
        f"> Eles definem a personalidade e o feel do produto.",
        "",
        "---",
        "",
        "## Comportamento de scroll e navegação",
        "",
    ]

    L.append(f"- Scroll suave: `{'sim' if inter['smooth_scroll'] else 'não detectado'}`")
    L.append(f"- Elementos sticky (navbar/sidebar): `{'sim' if inter['sticky'] else 'não detectado'}`")
    L.append("")

    if inter['smooth_scroll']:
        L += [
            "```css",
            "html { scroll-behavior: smooth; }",
            "```",
            "",
        ]

    if anim['keyframes']:
        L += ["## Animações (@keyframes)", ""]
        for kf in anim['keyframes']:
            L.append(f"- `@keyframes {kf}`")
        L.append("")

    if anim['durations']:
        L.append(f"**Durações de animação detectadas**: {', '.join(f'`{d}`' for d in anim['durations'])}")
        L.append("")

    if anim['transitions']:
        L += ["## Transições CSS", "", "```css"]
        for t in anim['transitions']:
            L.append(f"transition: {t};")
        L += ["```", ""]

    if inter['hover']:
        L += ["## Estados :hover", ""]
        for h in inter['hover']:
            L += [
                f"```css",
                f"{h['selector']}:hover {{",
            ]
            for p in h['properties']:
                L.append(f"  {p};")
            L += ["}", "```", ""]

    if inter['focus']:
        L += ["## Estados :focus (acessibilidade)", ""]
        for f in inter['focus']:
            L += [
                "```css",
                f"{f['selector']}:focus {{",
            ]
            for p in f['properties']:
                L.append(f"  {p};")
            L += ["}", "```", ""]

    if inter['js_events']:
        L += [
            "## Eventos JavaScript identificados",
            "",
            "Os seguintes eventos estão implementados no `scripts/main.js`:",
            "",
        ]
        for evt in inter['js_events']:
            L.append(f"- `{evt}`")
        L.append("")
        L.append("Mantenha estes comportamentos ao refatorar o JavaScript.")
        L.append("")

    # Diretrizes de UX
    L += [
        "## Diretrizes de UX para novas funcionalidades",
        "",
        "Ao adicionar novos elementos, siga estas regras extraídas do design original:",
        "",
        "1. **Consistência de interação** — use as mesmas durações de transição já definidas",
        "2. **Feedback visual** — todo elemento clicável deve ter estado :hover documentado acima",
        "3. **Acessibilidade** — mantenha estados :focus visíveis conforme padrão do projeto",
        "4. **Mobile first** — valide o comportamento nos breakpoints documentados em `layout-system.md`",
        "",
        "---",
        "",
        f"*Process Cloner — {now}*",
    ]
    return '\n'.join(L)


def _build_claude_prompts(dna: dict, title: str, now: str, paths: dict) -> str:
    comp_names = [c['name'] for c in dna['components']]
    comp_list  = ', '.join(comp_names[:6]) if comp_names else 'navbar, hero, cards, footer'
    top_colors = dna['colors']['top'][:3]
    color_str  = ', '.join(top_colors) if top_colors else 'as cores do design-tokens.md'
    fonts      = dna['typography']['families']
    font_str   = fonts[0] if fonts else 'fonte documentada no design-tokens.md'
    max_w      = dna['layout'].get('max_width') or '1200px'
    has_flex   = dna['layout']['flexbox']
    has_grid   = dna['layout']['grid']
    layout_str = ' e '.join(filter(None, ['Flexbox' if has_flex else '', 'CSS Grid' if has_grid else ''])) or 'layout padrão'

    L = [
        f"# Prompts para Claude Code — {title}",
        f"> Gerado pelo Process Cloner em {now}",
        f"> Copie e cole estes prompts diretamente no Claude Code.",
        f"> Eles já referenciam os arquivos de skill corretos.",
        "",
        "---",
        "",
        "## Como usar",
        "",
        "1. Abra o terminal na pasta `output/`",
        "2. Execute: `claude`",
        "3. Copie um dos prompts abaixo e cole",
        "",
        "---",
        "",
        "## Prompt 1 — Personalizar conteúdo mantendo o design",
        "",
        "```",
        f"Leia os arquivos da pasta skills/ antes de qualquer alteração:",
        f"- skills/design-tokens.md → paleta de cores e tipografia",
        f"- skills/layout-system.md → grid e breakpoints",
        f"- skills/components.md → estrutura de cada componente",
        f"- skills/ux-patterns.md → animações e interações",
        "",
        f"Vou personalizar o projeto em output/index.html.",
        f"Regras obrigatórias:",
        f"- Preserve TODAS as cores: {color_str}",
        f"- Preserve a fonte: {font_str}",
        f"- Mantenha o container com max-width: {max_w}",
        f"- Mantenha o sistema de layout: {layout_str}",
        f"- Os componentes existentes ({comp_list}) devem continuar funcionando",
        "",
        f"Minha personalização:",
        f"[DESCREVA AQUI O QUE QUER MUDAR]",
        "```",
        "",
        "---",
        "",
        "## Prompt 2 — Criar nova seção respeitando o design system",
        "",
        "```",
        f"Leia skills/design-tokens.md e skills/components.md.",
        "",
        f"Crie uma nova seção HTML para inserir em output/index.html.",
        f"A seção deve seguir exatamente o design system do projeto:",
        f"- Usar apenas as cores de skills/design-tokens.md",
        f"- Usar a fonte {font_str}",
        f"- Seguir o grid documentado em skills/layout-system.md",
        f"- Ter os mesmos padrões de hover/transição de skills/ux-patterns.md",
        "",
        f"A nova seção é:",
        f"[DESCREVA A SEÇÃO: ex. 'seção de FAQ com 5 perguntas sobre o produto']",
        "```",
        "",
        "---",
        "",
        "## Prompt 3 — Corrigir responsividade",
        "",
        "```",
        f"Leia skills/layout-system.md para ver os breakpoints do projeto.",
        "",
        f"Analise output/index.html e styles/styles.css.",
        f"Corrija os problemas de responsividade respeitando os breakpoints documentados.",
        "",
        f"Prioridade:",
        f"1. Mobile ({dna['layout']['breakpoints'][0] if dna['layout']['breakpoints'] else '768px'} ou menor)",
        f"2. Tablet",
        f"3. Desktop",
        "",
        f"Não altere cores, fontes nem estrutura de componentes.",
        "```",
        "",
        "---",
        "",
        "## Prompt 4 — Adicionar interatividade JavaScript",
        "",
        "```",
        f"Leia skills/ux-patterns.md para entender os padrões de interação do projeto.",
        "",
        f"Adicione a seguinte funcionalidade em scripts/main.js:",
        f"[DESCREVA A FUNCIONALIDADE: ex. 'menu mobile hamburguer que abre/fecha']",
        "",
        f"Regras:",
        f"- Use vanilla JS (sem jQuery ou frameworks)",
        f"- Siga as durações de transição documentadas em ux-patterns.md",
        f"- Adicione estados :hover e :focus conforme o padrão do projeto",
        f"- O código deve funcionar nos navegadores modernos",
        "```",
        "",
        "---",
        "",
        "## Prompt 5 — Auditoria completa do projeto",
        "",
        "```",
        f"Leia todos os arquivos da pasta skills/:",
        f"- skills/design-tokens.md",
        f"- skills/layout-system.md",
        f"- skills/components.md",
        f"- skills/ux-patterns.md",
        "",
        f"Depois analise output/index.html e styles/styles.css.",
        "",
        f"Faça uma auditoria e liste:",
        f"1. Inconsistências de cor (cores que não estão no design-tokens.md)",
        f"2. Problemas de responsividade",
        f"3. Componentes com HTML semântico incorreto",
        f"4. Estados de interação faltando (:hover, :focus)",
        f"5. Oportunidades de melhoria de performance CSS",
        "",
        f"Priorize por impacto visual no usuário.",
        "```",
        "",
        "---",
        "",
        "## Prompt 6 — Preparar para produção",
        "",
        "```",
        f"Leia skills/layout-system.md e skills/ux-patterns.md.",
        "",
        f"Prepare o projeto output/ para deploy em produção:",
        f"1. Valide o HTML semântico (tags corretas, alt em imagens, aria-labels)",
        f"2. Verifique se todas as imagens têm fallback",
        f"3. Confirme que o CSS não tem regras duplicadas",
        f"4. Valide responsividade nos breakpoints documentados",
        f"5. Adicione meta tags de SEO básico ao index.html",
        f"6. Confirme que scripts/main.js não tem erros de console",
        "",
        f"Não altere nenhum estilo visual — apenas qualidade e correção.",
        "```",
        "",
        "---",
        "",
        f"*Process Cloner — {now}*",
    ]
    return '\n'.join(L)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _top_classes(el, n=6) -> List[str]:
    """Retorna as classes CSS mais relevantes de um elemento."""
    classes = el.get('class', [])
    return [c for c in classes if len(c) > 1][:n]

def _read(path: str) -> str:
    if path and os.path.exists(path):
        try:
            return open(path, encoding='utf-8', errors='replace').read()
        except Exception:
            pass
    return ''
