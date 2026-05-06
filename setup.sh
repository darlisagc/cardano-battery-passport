#!/usr/bin/env bash
# Setup do workshop DPP - idempotente.
#
# Verifica o ambiente antes de instalar:
#   1. Python 3.11+ ja presente?
#   2. .venv ja criado?
#   3. Cada dependencia ja instalada (pip show)?
#   4. .env ja preenchido?
#
# Uso:  bash setup.sh
#
# Roda quantas vezes quiser - so instala/cria o que estiver faltando.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

ok()    { echo -e "${GREEN}✓${RESET} $1"; }
warn()  { echo -e "${YELLOW}!${RESET} $1"; }
err()   { echo -e "${RED}✗${RESET} $1"; }

echo "=== 1. Verificando Python 3.11+ ==="
if ! command -v python3 &> /dev/null; then
    err "python3 nao encontrado. Instale Python 3.11+: https://www.python.org/downloads/"
    exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]); then
    err "Python 3.11+ requerido. Voce tem $PY_VERSION."
    exit 1
fi
ok "Python $PY_VERSION"

echo
echo "=== 2. Verificando virtualenv (.venv) ==="
if [ -d ".venv" ]; then
    ok ".venv ja existe - reutilizando"
else
    echo "Criando .venv..."
    python3 -m venv .venv
    ok ".venv criado"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# upgrade pip silenciosamente se nao for recente
pip install --quiet --upgrade pip 2>/dev/null || true

echo
echo "=== 3. Verificando dependencias ==="
MISSING=()
while IFS= read -r line; do
    # pula comentarios e linhas em branco
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// /}" ]] && continue

    # nome do pacote (lida com >=, <, ==, !=, ~=)
    PKG=$(echo "$line" | sed -E 's/[<>=!~].*//' | tr -d '[:space:]')

    if pip show "$PKG" &> /dev/null; then
        VERSION=$(pip show "$PKG" 2>/dev/null | awk '/^Version:/ {print $2}')
        ok "$PKG ($VERSION) ja instalado"
    else
        warn "$PKG faltando"
        MISSING+=("$line")
    fi
done < requirements.txt

if [ ${#MISSING[@]} -eq 0 ]; then
    ok "Todas as dependencias ja estao instaladas - nada para baixar."
else
    echo
    echo "Instalando ${#MISSING[@]} pacote(s) faltante(s)..."
    pip install -r requirements.txt
    ok "Dependencias instaladas"
fi

# Verifica conflitos de versao depois (sem falhar setup se pip check reclamar de extras)
echo
if pip check &> /dev/null; then
    ok "Sem conflitos de versao"
else
    warn "pip check encontrou avisos - rode 'pip check' para detalhes"
fi

echo
echo "=== 4. Verificando .env ==="
if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env criado a partir de .env.example. PREENCHA antes de continuar:"
    echo "    - BLOCKFROST_PROJECT_ID  (preprod...)"
    echo "    - WALLET_MNEMONIC        (24 palavras, TESTNET ONLY)"
else
    ok ".env ja existe"
    # Verifica preenchimento basico (sem mostrar secrets)
    if grep -q "preprodXXXX" .env 2>/dev/null; then
        warn "BLOCKFROST_PROJECT_ID parece ser o placeholder - preencha o valor real"
    fi
    if grep -q "^WALLET_MNEMONIC=$" .env 2>/dev/null || grep -q "^WALLET_MNEMONIC=$" .env 2>/dev/null; then
        warn "WALLET_MNEMONIC parece vazio - preencha o mnemonico (TESTNET ONLY)"
    fi
fi

echo
ok "Setup concluido."
echo
echo "Para usar o ambiente nesta sessao do shell:"
echo "    source .venv/bin/activate"
echo
echo "Para rodar o primeiro ator:"
echo "    PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator origem"
