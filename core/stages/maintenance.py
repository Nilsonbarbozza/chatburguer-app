"""
core/stages/maintenance.py
Stage 4 — Injeção de comentários estruturais no HTML
"""
import logging
from typing import Dict, Any
from bs4 import Comment
from core.pipeline import ProcessorStage
from core.utils import setup_logging

setup_logging()
logger = logging.getLogger('html_processor')


class MaintenanceStage(ProcessorStage):
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=== ETAPA 4: Comentários Estruturais ===")
        soup = context['soup']

        role_labels = {
            'banner':        '[SECTION] Cabeçalho / Header',
            'navigation':    '[SECTION] Navegação',
            'main':          '[SECTION] Conteúdo Principal',
            'complementary': '[SECTION] Sidebar',
            'contentinfo':   '[SECTION] Rodapé',
            'search':        '[SECTION] Busca',
            'region':        '[SECTION] Região de Destaque',
        }
        for role, label in role_labels.items():
            for el in soup.find_all(attrs={'role': role}):
                el.insert(0, Comment(f" {label} "))

        tag_labels = [
            ('header',  '[COMPONENT] Header Principal'),
            ('footer',  '[COMPONENT] Rodapé Principal'),
            ('main',    '[LAYOUT] Conteúdo Principal'),
            ('nav',     '[LAYOUT] Menu de Navegação'),
            ('aside',   '[LAYOUT] Barra Lateral (Sidebar)'),
            ('article', '[COMPONENT] Artigo de Conteúdo'),
            ('section', '[LAYOUT] Seção Estrutural'),
        ]
        for tag, label in tag_labels:
            for el in soup.find_all(tag):
                # Verifica se já tem comentário ou data-attribute
                component_info = el.get('data-cloner-component')
                section_info = el.get('data-cloner-section')
                
                final_label = label
                if component_info: final_label = f"[COMPONENT] {component_info}"
                elif section_info: final_label = f"[SECTION] {section_info}"
                
                if not any(isinstance(c, Comment) and "[SECTION]" in str(c) for c in el.children):
                    el.insert(0, Comment(f" {final_label} "))

        logger.info("Comentários estruturais injetados")
        context['soup'] = soup
        return context
