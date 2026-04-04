#!/usr/bin/env bash
# ============================================================
# Process Cloner v1.0 — Instalador Linux / macOS
# ============================================================
set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}"
echo "  ██████╗ ██╗      ██████╗ ███╗  ██╗███████╗██████╗"
echo " ██╔════╝ ██║     ██╔═══██╗████╗ ██║██╔════╝██╔══██╗"
echo " ██║      ██║     ██║   ██║██╔██╗██║█████╗  ██████╔╝"
echo " ██║      ██║     ██║   ██║██║╚████║██╔══╝  ██╔══██╗"
echo " ╚██████╗ ███████╗╚██████╔╝██║ ╚███║███████╗██║  ██║"
echo "  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚══╝╚══════╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "${BOLD}  Process Cloner v1.0.3 — Instalador${NC}"
echo "  ─────────────────────────────────"
echo ""

# ── Verifica Python ──
echo -e "${CYAN}[1/4] Verificando Python...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado.${NC}"
    echo "  Instale em: https://www.python.org/downloads/"
    exit 1
fi
PY_VERSION=$(python3 --version 2>&1)
echo -e "${GREEN}  ✅ ${PY_VERSION}${NC}"

# ── Instala dependências Python ──
echo ""
echo -e "${CYAN}[2/4] Instalando dependências Python...${NC}"
python3 -m pip install --upgrade pip -q
python3 -m pip install -r requirements.txt -q
echo -e "${GREEN}  ✅ Dependências instaladas${NC}"

# ── Verifica Node.js (opcional) ──
echo ""
echo -e "${CYAN}[3/4] Verificando ferramentas Node.js (opcionais)...${NC}"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    echo -e "${GREEN}  ✅ Node.js ${NODE_VER}${NC}"

    install_npm_tool() {
        local tool=$1
        if command -v $tool &>/dev/null; then
            echo -e "${GREEN}  ✅ ${tool} já instalado${NC}"
        else
            echo -e "${YELLOW}  📦 Instalando ${tool}...${NC}"
            npm install -g $tool -q && echo -e "${GREEN}  ✅ ${tool} instalado${NC}" \
                || echo -e "${YELLOW}  ⚠️  ${tool} falhou (não obrigatório)${NC}"
        fi
    }

    install_npm_tool prettier
    install_npm_tool lightningcss
    install_npm_tool purgecss
else
    echo -e "${YELLOW}  ⚠️  Node.js não encontrado.${NC}"
    echo "    Ferramentas de otimização CSS serão puladas."
    echo "    Instale em: https://nodejs.org"
fi

# ── Cria .env ──
echo ""
echo -e "${CYAN}[4/4] Configurando ambiente...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}  ✅ Arquivo .env criado a partir do .env.example${NC}"
else
    echo -e "${GREEN}  ✅ .env já existe${NC}"
fi

# ── Cria pastas necessárias ──
mkdir -p output logs

# ── Finalização ──
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════╗"
echo "║  ✅ Instalação concluída!         ║"
echo "╚══════════════════════════════════╝${NC}"
echo ""
echo -e "  Para usar, execute:"
echo -e "${BOLD}    python3 cloner.py${NC}"
echo ""
echo -e "  Ou com arquivo direto:"
echo -e "${BOLD}    python3 cloner.py --file caminho/para/arquivo.html${NC}"
echo ""
