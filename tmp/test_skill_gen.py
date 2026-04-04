import os
import sys
from bs4 import BeautifulSoup

# Adiciona o diretório atual ao path para importar core
sys.path.insert(0, os.getcwd())

from core.skill_generator import DesignAnalyzer

# Mock de dados
html = """
<html lang="en">
<head><title>Test Page</title></head>
<body>
    <header class="main-header">
        <nav class="nav-bar"><ul><li>Home</li></ul></nav>
    </header>
    <main id="app">
        <section class="hero"><h1>Welcome</h1></section>
        <button class="btn-primary">Click me</button>
    </main>
</body>
</html>
"""

css = """
:root {
    --primary-color: #3498db;
    --bg-main: rgb(255, 255, 255);
    --text-dark: hsl(210, 10%, 23%);
}
body {
    background-color: var(--bg-main);
    color: var(--text-dark);
    font-family: 'Inter', sans-serif;
}
.btn-primary {
    background: var(--primary-color);
    padding: 10px 20px;
    border-radius: 5px;
}
@media (max-width: 768px) {
    body { font-size: 14px; }
}
"""

def test_analysis():
    soup = BeautifulSoup(html, 'html.parser')
    analyzer = DesignAnalyzer(soup, css, html, 'images/')
    dna = analyzer.extract()
    
    print("=== CORES ===")
    print(f"Top 5: {dna['colors']['top'][:5]}")
    print(f"Semântica: {dna['colors']['semantic']}")
    
    print("\n=== LAYOUT ===")
    print(f"Breakpoints: {dna['layout']['breakpoints']}")
    print(f"Sections: {dna['layout']['sections']}")
    
    print("\n=== VARS ===")
    print(f"Vars: {list(dna['css_vars'].keys())}")

    # Asserts básicos
    assert '#3498DB' in dna['colors']['top']
    assert dna['colors']['semantic']['background'] == '#FFFFFF'
    assert '768px' in dna['layout']['breakpoints']
    print("\n✅ Teste concluído com sucesso!")

if __name__ == "__main__":
    test_analysis()
