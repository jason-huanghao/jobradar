#!/usr/bin/env bash
# JobRadar one-shot installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
# Or:    git clone https://github.com/jason-huanghao/jobradar.git && cd jobradar && bash install.sh

set -e

REPO_URL="https://github.com/jason-huanghao/jobradar.git"

# ── Detect install directory ────────────────────────────────────────
# When used as an OpenClaw skill, install into the agents skills root
# so OpenClaw can discover it without symlink path restrictions.
if [ -n "$JOBRADAR_DIR" ]; then
  INSTALL_DIR="$JOBRADAR_DIR"
elif [ -d "$HOME/.agents/skills" ]; then
  # OpenClaw agents-skills-personal root (preferred for skill visibility)
  INSTALL_DIR="$HOME/.agents/skills/jobradar"
else
  INSTALL_DIR="$HOME/.jobradar"
fi

echo ""
echo "⚡ JobRadar Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Clone or update ─────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "📦 Updating existing install at $INSTALL_DIR …"
  cd "$INSTALL_DIR"
  git pull --quiet
else
  echo "📦 Cloning JobRadar to $INSTALL_DIR …"
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ── Step 2: Python check ────────────────────────────────────────────
PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3 || true)
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3.11+ required. Install from https://python.org"
  exit 1
fi
PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python $PYVER → $PYTHON"

# ── Step 3: Virtualenv ──────────────────────────────────────────────
if [ ! -d "$INSTALL_DIR/.venv" ]; then
  echo "🔧 Creating virtualenv …"
  $PYTHON -m venv "$INSTALL_DIR/.venv"
fi
VENV="$INSTALL_DIR/.venv"
PIP="$VENV/bin/pip"
JOBRADAR="$VENV/bin/jobradar"

echo "📥 Installing dependencies …"
$PIP install --upgrade pip --quiet
$PIP install -e ".[all]" --quiet

# ── Step 4: Shell integration (add to PATH) ─────────────────────────
SHELL_RC=""
case "$SHELL" in
  */zsh)  SHELL_RC="$HOME/.zshrc"  ;;
  */bash) SHELL_RC="$HOME/.bashrc" ;;
esac

if [ -n "$SHELL_RC" ] && ! grep -q "jobradar" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# JobRadar" >> "$SHELL_RC"
  echo "export PATH=\"$VENV/bin:\$PATH\"" >> "$SHELL_RC"
  echo "export JOBRADAR_DIR=\"$INSTALL_DIR\"" >> "$SHELL_RC"
  echo "✅ Added jobradar to PATH in $SHELL_RC"
fi

# Also export for current session
export PATH="$VENV/bin:$PATH"
export JOBRADAR_DIR="$INSTALL_DIR"

# ── Step 5: Summary ─────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ JobRadar installed at: $INSTALL_DIR"
echo ""
echo "🚀 Quick start:"
echo "   jobradar run --cv <your-cv-url>    # find jobs using your CV"
echo "   jobradar report                    # generate HTML report"
echo "   jobradar health                    # check config"
echo ""
if [ -d "$HOME/.agents/skills/jobradar" ]; then
  echo "🦞 OpenClaw skill: ready"
  echo "   Restart OpenClaw gateway to load: openclaw gateway stop && openclaw gateway --force &"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
