import pytest
import time
import re
from bs4 import BeautifulSoup
from core.stages.dataclear import DataClearStage

# ==========================================
# FIXTURES (DADOS SINTÉTICOS DE LABORATÓRIO)
# ==========================================
# ==========================================
# FIXTURES (DADOS SINTÉTICOS DE NÍVEL GLOBAL)
# ==========================================

# 1. HTML PII HOSTIL (Multilíngue, UTF-8 Extremo e Caos de Regex)
HTML_PII_HOSTIL = """
<main role="main">
    <h1>Global Enterprise Directory 🌍</h1>
    
    <h2>Brazil (Operações)</h2>
    <p>Contato financeiro (João): +55 (11) 98765-4321. Suporte: 0800 123 4567. E-mail: joao.financas@empresa.com.br.</p>
    
    <h2>USA (Headquarters)</h2>
    <p>Call our Toll-Free at 1-800-555-0199 or reach the CEO at john_doe.executive@corp-ventures.us.</p>
    
    <h2>Germany (Engineering)</h2>
    <p>Kontaktieren Sie Herrn Müller unter +49 151 2345 6789. Wichtig: E-Mail an info@müller-gmbh.de senden.</p>
    
    <h2>Spain (Logistics)</h2>
    <p>Para envíos, llame al +34 91 123 45 67. Correo electrónico: logística_madrid@empresa.es.</p>

    <h2>Japan (Hardware Supply)</h2>
    <p>サポート窓口：+81 90-1234-5678 までお電話ください。部品リンク: <a href="https://amazon.co.jp/itm/9999988888">https://amazon.co.jp/itm/9999988888</a></p>
</main>
"""

# 2. HTML STRICT (Ruído Real de E-commerce / Notícias)
HTML_STRICT_RUIDO = """
<main role="main">
    <div id="CybotCookiebotDialog" class="cookie-banner">
        Aceite nossos cookies para continuar navegando. <button>Aceitar</button>
    </div>
    
    <header><nav>Home > Produtos > Apple</nav></header>

    <h1>MacBook Pro 16" M3 Max</h1>
    <p>O processador mais avançado da categoria, com bateria para o dia todo.</p>
    
    <div class="sponsored-ad">
        <p>Patrocinado: Compre capas para seu MacBook aqui!</p>
    </div>

    ## Leia mais
    <ul>
        <li><a href="#">Veja também: iPhones em promoção</a></li>
        <li><a href="#">[Pule para recomendações](#)</a></li>
    </ul>
    
    <footer>© 2026 E-commerce Global. Todos os direitos reservados.</footer>
</main>
"""

# ==========================================
# BATERIA 1: TESTES DE REGRESSÃO E HIGIENE (PII)
# ==========================================
def test_pii_redaction_and_url_shield():
    """Garante que a engenharia PII bloqueia dados sensíveis, mas preserva o Escudo de URL."""
    agente = DataClearStage(redact_pii=True, strict=False)
    soup = BeautifulSoup(HTML_PII_HOSTIL, 'lxml')
    contexto_mock = {'soup': soup, 'url': 'https://amazon.co.jp/itm/9999988888'}
    
    resultado = agente.process(contexto_mock)
    markdown_limpo = resultado['dataset_entry']['content']['markdown_body']
    
    # Asserções de Segurança (Se alguma falhar, o teste quebra)
    assert "[REDACTED_PHONE]" in markdown_limpo, "Falha Crítica: Telefone não foi mascarado!"
    assert "[REDACTED_EMAIL]" in markdown_limpo, "Falha Crítica: E-mail não foi mascarado!"
    assert "https://amazon.co.jp/itm/9999988888" in markdown_limpo, "Falha no Escudo: URL destruída!"

# ==========================================
# BATERIA 2: TESTES DE PODA SEMÂNTICA (STRICT MODE)
# ==========================================
def test_strict_mode_semantic_pruning():
    """Garante que a guilhotina do Strict Mode corta o lixo publicitário."""
    agente = DataClearStage(redact_pii=False, strict=True)
    soup = BeautifulSoup(HTML_STRICT_RUIDO, 'lxml')
    contexto_mock = {'soup': soup, 'url': 'https://teste.com'}
    
    resultado = agente.process(contexto_mock)
    markdown_limpo = resultado['dataset_entry']['content']['markdown_body']
    
    # Asserções de Limpeza
    assert "MacBook Pro 16" in markdown_limpo, "O conteúdo principal sumiu!"
    assert "patrocinado" not in markdown_limpo.lower(), "Lixo publicitário retido."
    assert "cookiebot" not in markdown_limpo.lower(), "Banner de cookie retido."

# ==========================================
# BATERIA 3: TESTE MASSIVO DE CONTINUIDADE (STRESS TEST)
# ==========================================
def test_massive_file_processing_performance():
    """
    Injeta um arquivo HTML massivo simulando varreduras de clientes Enterprise.
    Valida a continuidade do sistema e a ausência de gargalos de memória (OOM).
    """
    # Gera um arquivo sintético com 5.000 parágrafos (~5MB de HTML puro)
    html_massivo = "<main>" + "<p>Processando linha de log do cliente. Contato: 0800 123 4567. Link: https://teste.com/log</p>" * 5000 + "</main>"
    soup = BeautifulSoup(html_massivo, 'lxml')
    
    # Ativa todos os motores pesados ao mesmo tempo
    agente = DataClearStage(redact_pii=True, strict=True)
    contexto_mock = {'soup': soup, 'url': 'https://extracao-massiva.com'}
    
    print("\n[STRESS TEST] Iniciando digestão de 5.000 nós DOM...")
    tempo_inicio = time.time()
    
    resultado = agente.process(contexto_mock)
    
    tempo_fim = time.time()
    tempo_total = tempo_fim - tempo_inicio
    
    markdown_limpo = resultado['dataset_entry']['content']['markdown_body']
    chunks = resultado['dataset_entry']['content']['semantic_chunks']
    
    # Asserções de Alta Performance
    assert resultado is not None
    assert "[REDACTED_PHONE]" in markdown_limpo
    assert len(chunks) > 10, "O fatiamento de chunks falhou no arquivo gigante!"
    
    # O pipeline DEVE ser capaz de limpar 5000 parágrafos em menos de 3.5 segundos.
    assert tempo_total < 3.5, f"Alerta de Gargalo: O processamento demorou muito ({tempo_total:.2f}s)!"
