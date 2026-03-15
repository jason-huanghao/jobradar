#!/usr/bin/env bash
# JobRadar — Automated Setup Script
# Usage: bash setup.sh [--cv /path/to/cv.md] [--key YOUR_API_KEY]
# One-liner: git clone https://github.com/jason-huanghao/jobradar.git && cd jobradar && bash setup.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CV_PATH=""
API_KEY=""
API_VAR="ARK_API_KEY"

while [[ $# -gt 0 ]]; do
  case $1 in
    --cv)  CV_PATH="$2"; shift 2 ;;
    --key) API_KEY="$2"; shift 2 ;;
    *)     shift ;;
  esac
done

echo "========================================"; echo "  JobRadar Setup"; echo "========================================"

# Step 1: Python 3.11+
PY=$(command -v python3 || command -v python || err "Python 3.11+ required")
PY_MINOR=$($PY -c "import sys; print(sys.version_info.minor)")
PY_VER=$($PY -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
[[ ${PY_MINOR} -lt 11 ]] && err "Python 3.11+ required (found $PY_VER)"
ok "Python $PY_VER"

# Step 2: Venv
if [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
  $PY -m venv "$SCRIPT_DIR/.venv"
  ok "Virtual environment created"
else
  ok "Virtual environment exists"
fi
PIP="$SCRIPT_DIR/.venv/bin/pip"
JOBRADAR="$SCRIPT_DIR/.venv/bin/jobradar"

# Step 3: Install
echo "Installing dependencies (~60s on first run)..."
$PIP install --upgrade pip hatchling -q
$PIP install -e "$SCRIPT_DIR/.[all]" -q
ok "Package installed"

# Step 4: Config
[[ ! -f "$SCRIPT_DIR/config.yaml" ]] && cp "$SCRIPT_DIR/config.example.yaml" "$SCRIPT_DIR/config.yaml"
ok "config.yaml ready"

# Step 5: API key — probe environment + .env
if [[ -z "$API_KEY" ]]; then
  for VAR in OPENCLAW_API_KEY OPENCODE_API_KEY ARK_API_KEY ZAI_API_KEY OPENAI_API_KEY DEEPSEEK_API_KEY ANTHROPIC_API_KEY OPENROUTER_API_KEY; do
    VAL="${!VAR:-}"
    if [[ -n "$VAL" && "$VAL" != "your_"* && "$VAL" != "sk-your"* ]]; then
      API_KEY="$VAL"; API_VAR="$VAR"
      ok "Auto-detected key from env: \$$VAR"
      break
    fi
  done
fi
if [[ -z "$API_KEY" && -f "$SCRIPT_DIR/.env" ]]; then
  while IFS='=' read -r k v; do
    [[ "$k" =~ ^#.*$ || -z "$k" ]] && continue
    for VAR in OPENCLAW_API_KEY OPENCODE_API_KEY ARK_API_KEY ZAI_API_KEY OPENAI_API_KEY DEEPSEEK_API_KEY ANTHROPIC_API_KEY; do
      if [[ "$k" == "$VAR" && -n "$v" && "$v" != "your_"* ]]; then
        API_KEY="$v"; API_VAR="$VAR"; ok "Found key in .env: $VAR"; break 2; fi
    done
  done < "$SCRIPT_DIR/.env"
fi
[[ ! -f "$SCRIPT_DIR/.env" ]] && cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
if [[ -n "$API_KEY" ]]; then
  grep -q "^$API_VAR=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "$API_VAR=$API_KEY" >> "$SCRIPT_DIR/.env"
  ok "API key in .env ($API_VAR)"
else
  warn "No API key found — run 'jobradar init' to set one"
fi

# Step 6: CV
if [[ -n "$CV_PATH" && -f "$CV_PATH" ]]; then
  python3 -c "import re; txt=open('$SCRIPT_DIR/config.yaml').read(); txt=re.sub(r'cv_path:.*','cv_path: $CV_PATH',txt); open('$SCRIPT_DIR/config.yaml','w').write(txt)"
  ok "CV path set: $CV_PATH"
fi

# Step 7: Health check
echo ""; echo "Running health check..."
cd "$SCRIPT_DIR"
"$JOBRADAR" health 2>&1 || warn "Health check incomplete — run 'jobradar init'"
echo ""
echo "========================================"; ok "Setup complete!"
echo ""; echo "Next: jobradar init   (interactive CV + key wizard)"
echo "Then: jobradar update --mode quick --limit 3"
echo "========================================"
