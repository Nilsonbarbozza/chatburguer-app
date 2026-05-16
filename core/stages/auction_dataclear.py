import re
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dateutil import parser as date_parser
from price_parser import Price

logger = logging.getLogger('html_processor')

class AuctionDataClear:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    def _enrich_auction_item(self, raw_data: dict) -> dict:
        """
        Normaliza e enriquece um item de leilão bruto.
        """
        text = raw_data.get("texto_bruto", "")
        text_lower = text.lower()
        
        # 1. Identificador Único
        from urllib.parse import urlparse
        href = raw_data.get("links_vital", {}).get("href", "")
        path = urlparse(href).path.lower()
        id_lote = "N/A"
        
        # Sniper: Extrai ID de caminhos como /lote/A9876 ou /item/123
        path_parts = [p for p in path.split('/') if p]
        if len(path_parts) >= 2 and any(kw in path_parts[-2] for kw in ['lote', 'item', 'anuncio', 'bem', 'produto']):
            id_lote = path_parts[-1].upper()
        else:
            # Fallback para padrões legados ou IDs embutidos
            id_match = re.search(r'[jxl](\d+)', path)
            if id_match:
                id_lote = id_match.group(1).upper()
            elif path_parts:
                # Se for o último segmento e tiver números, tentamos como ID
                last = path_parts[-1]
                if any(c.isdigit() for c in last) and len(last) >= 3:
                    id_lote = last.upper()

        # 2. Localização (Deep Parser)
        cidade, estado, bairro = "Não informado", "NI", "Não informado"
        
        # Tenta extrair do texto primeiro
        loc_match = re.search(r'([\w\s]+)\s*-\s*([A-Z]{2})\s*,\s*([\w\s]+?)(?=\s*Área|\s*Status|\s*Valor|\s*Datas|$)', text, re.I)
        if loc_match:
            cidade = loc_match.group(1).strip()
            estado = loc_match.group(2).strip()
            bairro = loc_match.group(3).strip()
        else:
            # Fallback Sniper via URL
            url_match = re.search(r'/([a-z]{2})/([a-z0-9\-]+)/', href.lower())
            if url_match:
                potential_uf = url_match.group(1).upper()
                if potential_uf in ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SE', 'SP', 'TO']:
                    estado = potential_uf
                    cidade = url_match.group(2).replace('-', ' ').title()

        # 3. Financeiro
        financeiro = {
            "valor_avaliacao": 0.0,
            "lance_minimo_1_praca": 0.0,
            "lance_minimo_2_praca": 0.0,
            "moeda": "BRL"
        }
        
        prices = []
        for match in re.finditer(r'R\$\s*[\d\.,]+', text):
            price_obj = Price.fromstring(match.group(0))
            if price_obj and price_obj.amount_float:
                prices.append(price_obj.amount_float)
                
        if prices:
            prices.sort(reverse=True)
            financeiro["valor_avaliacao"] = prices[0]
            if len(prices) > 1:
                financeiro["lance_minimo_1_praca"] = prices[0]
                financeiro["lance_minimo_2_praca"] = prices[-1]
            else:
                financeiro["lance_minimo_1_praca"] = prices[0]
                financeiro["lance_minimo_2_praca"] = prices[0] * 0.5

        # 4. Cronograma
        cronograma = {"data_1_praca": None, "data_2_praca": None}
        dates_raw = raw_data.get("datas_leilao", [])
        parsed_dates = []
        for d in dates_raw:
            try:
                parsed = date_parser.parse(d, dayfirst=True, fuzzy=True)
                if not parsed.tzinfo: parsed = parsed.replace(tzinfo=timezone.utc)
                parsed_dates.append(parsed)
            except: pass
        
        parsed_dates.sort()
        if parsed_dates:
            cronograma["data_1_praca"] = parsed_dates[0].strftime("%Y-%m-%dT%H:%M:%SZ")
            if len(parsed_dates) > 1:
                cronograma["data_2_praca"] = parsed_dates[-1].strftime("%Y-%m-%dT%H:%M:%SZ")

        # 5. Detalhes
        area_metragem = 0.0
        area_raw = raw_data.get("area_metragem", "")
        if area_raw:
            area_obj = Price.fromstring(str(area_raw))
            if area_obj and area_obj.amount_float:
                area_metragem = area_obj.amount_float

        return {
            "id_lote": id_lote,
            "status_leilao": raw_data.get("status_leilao") or "Desconhecido",
            "tipo_judicial": raw_data.get("tipo_judicial") or "Não Identificado",
            "tipo_imovel": raw_data.get("tipo_imovel") or "outros",
            "localizacao": {"cidade": cidade, "estado": estado, "bairro": bairro},
            "financeiro": financeiro,
            "cronograma": cronograma,
            "detalhes": {
                "area_metragem": area_metragem,
                "unidade_medida": "m2" if "m" in str(area_raw).lower() else "unknown",
                "comodos": raw_data.get("comodos") or {}
            },
            "links_vital": raw_data.get("links_vital") or {},
            "metadata": {
                "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }

    def process_auction(self, raw_items: list, base_url: str, context: dict) -> dict:
        """
        Refina e normaliza itens já extraídos pelo DataClearStage Sniper V4.
        """
        logger.info(f"=== Batalhão V3 Enterprise: Refinaria Acionada ===")
        
        refined_items = []
        for raw in raw_items:
            try:
                if not isinstance(raw, dict): continue
                refined = self._enrich_auction_item(raw)
                if refined:
                    refined_items.append(refined)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao refinar item: {e}")
                
        context["hub_items"] = refined_items
        
        # Envelopamento para Dataset
        context['dataset_entries'] = [{
            "id_hash": hashlib.sha256(base_url.encode()).hexdigest(),
            "url": base_url,
            "capture_id": context.get('capture_id', 'unknown'),
            "mission_id": context.get('mission_id', 'default'),
            "executor": context.get('executor_level', 'unknown'),
            "fidelity_score": 1.0,
            "data": {
                "title": f"Auction Grid: {len(refined_items)} lotes",
                "markdown_body": f"Refino concluído para {len(refined_items)} itens.",
                "semantic_chunks": [],
                "hub_items": refined_items
            }
        }]
        
        logger.info(f"✅ [AUCTION-REFINERY] Refino concluído: {len(refined_items)} cards em {base_url}")
        return context
