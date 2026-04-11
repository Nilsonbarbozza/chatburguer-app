"""
core/stages/refactoring.py
Stage 11 — Refatoração Semântica e Design System
Transforma o código capturado em uma estrutura profissional de boilerplate.
"""
import re
import logging
from collections import Counter
from typing import Dict, Any, List, Tuple
from bs4 import BeautifulSoup
from core.pipeline import ProcessorStage

logger = logging.getLogger('html_processor')

class RefactoringStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 11: Refatoração Semântica & Design System ===")
        
        css_content = context.get('css', '')
        soup = context.get('soup')
        
        if not css_content or not soup:
            return context

        # 1. Extração e Aplicação de Design Tokens (Variáveis CSS)
        design_tokens = self._extract_design_tokens(css_content)
        context['css'] = self._apply_design_tokens(css_content, design_tokens)
        
        # 2. Refatoração Semântica de Classes (Opcional - Alta Fidelidade)
        class_map = self._generate_semantic_map(soup, context)
        context['css'] = self._apply_class_renames_to_css(context['css'], class_map)
        self._apply_class_renames_to_html(soup, class_map)

        # 3. Adição de Metadados Semânticos ao HTML
        self._add_semantic_metadata(soup)
        
        return context

    def _extract_design_tokens(self, css: str) -> Dict[str, Any]:
        """Identifica padrões de cores e fontes para criar um Design System em :root."""
        # Captura cores (Hex, RGB, RGBA)
        color_pattern = r'#(?:[0-9a-fA-F]{3}){1,2}\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)'
        colors = re.findall(color_pattern, css)
        color_counts = Counter(c.upper() for c in colors)
        
        # Filtra cores significativas (mínimo 3 repetições)
        # Ordenadas por frequência
        sorted_colors = [c for c, count in color_counts.most_common(20) if count >= 2]
        
        tokens = {
            "colors": {},
            "fonts": []
        }
        
        # Mapeamento semântico básico de cores
        color_map = {}
        for i, color in enumerate(sorted_colors):
            if i == 0: name = "--brand-primary"
            elif i == 1: name = "--brand-secondary"
            elif i == 2: name = "--brand-accent"
            elif "#F" in color or "255, 255, 255" in color: name = f"--bg-light-{i}"
            elif "#0" in color or "0, 0, 0" in color: name = f"--text-dark-{i}"
            else: name = f"--color-palette-{i}"
            color_map[color] = name
            
        tokens["colors"] = color_map
        
        # Captura fontes
        font_pattern = r'font-family:\s*([^;!]+)'
        fonts = re.findall(font_pattern, css)
        if fonts:
            # Pega a fonte mais comum do body/html
            most_common_font = Counter(fonts).most_common(1)[0][0].strip()
            tokens["fonts"] = [("--font-main", most_common_font)]
            
        return tokens

    def _apply_design_tokens(self, css: str, tokens: Dict[str, Any]) -> str:
        """Insere o bloco :root e substitui valores literais por variáveis."""
        root_block = ":root {\n"
        
        # Adiciona cores
        for color, var_name in tokens["colors"].items():
            root_block += f"  {var_name}: {color};\n"
            
        # Adiciona fontes
        for var_name, font_val in tokens["fonts"]:
            root_block += f"  {var_name}: {font_val};\n"
            
        root_block += "}\n\n"
        
        new_css = css
        
        # Substitui cores (case-insensitive para hex)
        for color, var_name in tokens["colors"].items():
            # Protege a substituição usando regex para evitar quebra em strings maiores
            pattern = re.escape(color)
            new_css = re.sub(pattern, f"var({var_name})", new_css, flags=re.IGNORECASE)
            
        # Substitui fontes
        for var_name, font_val in tokens["fonts"]:
            new_css = new_css.replace(font_val, f"var({var_name})")
            
        return root_block + new_css

    def _add_semantic_metadata(self, soup: BeautifulSoup):
        """Identifica seções lógicas e adiciona classes amigáveis e comentários."""
        # 1. Identifica Header
        header = soup.find(['header', 'nav']) or soup.find('div', class_=re.compile(r'header|nav|topbar', re.I))
        if header:
            header['data-cloner-component'] = "Main Header"
            self._ensure_class(header, "cloner-header")
            
        # 2. Identifica Footer
        footer = soup.find('footer') or soup.find('div', class_=re.compile(r'footer|bottom', re.I))
        if footer:
            footer['data-cloner-component'] = "Main Footer"
            self._ensure_class(footer, "cloner-footer")

        # 3. Identifica Seções (Main Content)
        sections = soup.find_all(['section', 'article'])
        for i, sec in enumerate(sections):
            sec['data-cloner-section'] = f"section-{i+1}"
            self._ensure_class(sec, f"cloner-section-{i+1}")

    def _generate_semantic_map(self, soup: BeautifulSoup, context: Dict[str, Any]) -> Dict[str, str]:
        """Cria um mapeamento de classes ofuscadas para nomes semânticos legíveis."""
        class_map = {}
        processed_classes = set()
        
        # Identifica o que é "JS Target" para evitar quebras
        js_content = context.get('js_bundle', '')
        
        # Heurística para classes ofuscadas (hashes curtos, prefixos de framework)
        # Ex: .sc-1g8o9, .css-481z, .jss123
        obscure_pattern = re.compile(r'^(sc-|css-|jss-|style_|[a-z0-9]{5,10}$)', re.I)

        # Mapeamento por contexto
        for tag in soup.find_all(True):
            classes = tag.get('class', [])
            if not classes: continue
            
            # Determina o prefixo semântico baseado no contêiner
            section_name = "component"
            parent = tag.find_parent(['header', 'footer', 'nav', 'section', 'article'])
            if parent:
                if parent.name == 'header': section_name = "header"
                elif parent.name == 'footer': section_name = "footer"
                elif parent.name == 'nav': section_name = "nav"
                elif 'hero' in ' '.join(parent.get('class', [])).lower(): section_name = "hero"
                else: section_name = parent.get('data-cloner-section', 'section')

            for cls in classes:
                if cls in processed_classes: continue
                
                # Se a classe parece ofuscada e não é um termo comum
                if obscure_pattern.match(cls) and len(cls) > 2:
                    # Verifica se é um alvo de JS
                    is_js_target = cls in js_content
                    
                    # Gera novo nome: prefixo-tag-index
                    new_name = f"{section_name}-{tag.name}-{len(class_map)}"
                    
                    # Regra: Se for JS Target, mantemos a original + adicionamos a nova.
                    # Mas no CSS, queremos que o usuário use a nova.
                    class_map[cls] = {
                        "new_name": new_name,
                        "keep_original": is_js_target
                    }
                    processed_classes.add(cls)
        
        logger.info(f"Mapeamento Semântico: {len(class_map)} classes identificadas para refatoração")
        return class_map

    def _apply_class_renames_to_css(self, css: str, class_map: Dict[str, Any]) -> str:
        """Substitui seletores de classe no CSS pelos novos nomes semânticos."""
        new_css = css
        for old_cls, info in class_map.items():
            # Regex para casar a classe como seletor (.classe) garantindo que não pegue partes de outras palavras
            # Casar .old_cls seguido de espaço, vírgula, chave ou pseudo-classe
            pattern = rf'\.{re.escape(old_cls)}(?=[ \s,{{:\[])'
            new_css = re.sub(pattern, f".{info['new_name']}", new_css)
        return new_css

    def _apply_class_renames_to_html(self, soup: BeautifulSoup, class_map: Dict[str, Any]):
        """Substitui ou adiciona classes no HTML conforme o mapeamento."""
        for tag in soup.find_all(class_=True):
            original_classes = tag.get('class', [])
            new_classes = []
            
            for cls in original_classes:
                if cls in class_map:
                    info = class_map[cls]
                    new_classes.append(info['new_name'])
                    if info['keep_original']:
                        new_classes.append(cls) # Mantém para compatibilidade com JS
                else:
                    new_classes.append(cls)
            
            tag['class'] = new_classes

    def _ensure_class(self, tag, new_class: str):
        existing = tag.get('class', [])
        if isinstance(existing, str): existing = [existing]
        if new_class not in existing:
            existing.append(new_class)
            tag['class'] = existing
