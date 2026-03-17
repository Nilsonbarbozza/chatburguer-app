#!/usr/bin/env bash
# ============================================================
# build.sh — Compila o Process Cloner em binário com PyInstaller
#
# Uso:
#   chmod +x build.sh
#   ./build.sh
#
# Saída:
#   dist/cloner          (Linux/Mac — executável único)
#   dist/cloner.exe      (Windows — via Wine ou CI Windows)
# ============================================================
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶ ${1}${NC}"; }
ok()    { echo -e "${GREEN}✅ ${1}${NC}"; }
warn()  { echo -e "${YELLOW}⚠  ${1}${NC}"; }
fail()  { echo -e "${RED}❌ ${1}${NC}"; exit 1; }

info "Process Cloner — Build Script"
echo "================================"

# ── Verifica dependências de build ──
info "Verificando dependências..."
python3 -m pip install pyinstaller -q || fail "Falha ao instalar PyInstaller"
ok "PyInstaller disponível"

# ── Gera SHA-256 do código fonte (rastreabilidade) ──
info "Calculando hash do fonte..."
find . -name "*.py" | sort | xargs sha256sum | sha256sum | awk '{print $1}' > build_hash.txt
ok "Hash gerado: $(cat build_hash.txt | cut -c1-16)..."

# ── Compila ──
info "Compilando binário (modo --onefile)..."
pyinstaller \
    --onefile \
    --name cloner \
    --add-data "core:core" \
    --add-data "cli:cli" \
    --hidden-import "bs4" \
    --hidden-import "lxml" \
    --hidden-import "cssutils" \
    --hidden-import "rich" \
    --hidden-import "dotenv" \
    --strip \
    --log-level WARN \
    cloner.py

if [ ! -f "dist/cloner" ]; then
    fail "Build falhou — dist/cloner não encontrado"
fi
ok "Binário gerado: dist/cloner"

# ── Calcula SHA-256 do binário gerado ──
info "Calculando SHA-256 do binário..."
if command -v sha256sum &>/dev/null; then
    SHA=$(sha256sum dist/cloner | awk '{print $1}')
else
    SHA=$(shasum -a 256 dist/cloner | awk '{print $1}')
fi
echo "$SHA  cloner" > dist/cloner.sha256
ok "SHA-256: $SHA"

# ── Empacota para distribuição ──
info "Empacotando para distribuição..."
VERSION=$(python3 -c "from cli.updater import CURRENT_VERSION; print(CURRENT_VERSION)")
ZIP_NAME="dist/process-cloner-v${VERSION}.zip"

# Inclui o binário + arquivos necessários (sem .py)
cd dist
zip -r "process-cloner-v${VERSION}.zip" cloner cloner.sha256 2>/dev/null || \
zip -r "process-cloner-v${VERSION}.zip" cloner.exe cloner.sha256 2>/dev/null
cd ..

# Adiciona assets ao ZIP (sem o código fonte)
zip "$ZIP_NAME" .env.example LEIA-ME.md LICENSE.md requirements.txt -q

ok "Pacote gerado: $ZIP_NAME"
echo ""
echo "═══════════════════════════════════════"
echo "  Build concluído com sucesso!"
echo "  Versão : v${VERSION}"
echo "  SHA-256: ${SHA:0:16}..."
echo "  Arquivo: $ZIP_NAME"
echo "═══════════════════════════════════════"
echo ""
echo "Próximos passos:"
echo "  1. Copie $ZIP_NAME para o servidor"
echo "  2. Copie dist/cloner.sha256 para o servidor"
echo "  3. Atualize LATEST_VERSION no .env do servidor"
echo "  4. Atualize LATEST_SHA256 no .env do servidor"
