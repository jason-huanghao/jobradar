#!/usr/bin/env bash
# JobRadar one-shot installer — works standalone and as an OpenClaw skill
#
# Usage (recommended):
#   bash <(curl -fsSL https://raw.githubusercontent.com/jason-huanghao/jobradar/main/install.sh)
#
# Or clone first:
#   git clone https://github.com/jason-huanghao/jobradar.git && cd jobradar && bash install.sh

set -e

REPO_URL="https://github.com/jason-huanghao/jobradar.git"

# ── Detect install directory ────────────────────────────────────────
# Priority: $JOBRADAR_DIR env → OpenClaw skills root → standalone ~/.jobradar
if [ -n "$JOBRADAR_DIR" ]; then
  INSTALL_DIR="$JOBRADAR_DIR"
elif [ -d "$HOME/.agents/skills" ]; then
  INSTALL_DIR="$HOME/.agents/skills/jobradar"
else
  INSTALL_DIR="$HOME/.jobradar"
fi

echo ""
echo "⚡ JobRadar Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Install dir: $INSTALL_DIR"
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
PYTHON=$(command -v python3.12 2>/dev/null \
      || command -v python3.11 2>/dev/null \
      || command -v python3    2>/dev/null \
      || true)
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

echo "📥 Installing dependencies (this takes ~30s on first run) …"
"$PIP" install --upgrade pip --quiet
# Install core only — CN sources and apply engine are optional extras
"$PIP" install -e "$INSTALL_DIR" --quiet

# ── Step 4: Shell PATH ──────────────────────────────────────────────
SHELL_RC=""
case "${SHELL:-}" in
  */zsh)  SHELL_RC="$HOME/.zshrc"  ;;
  */bash) SHELL_RC="$HOME/.bashrc" ;;
esac

if [ -n "$SHELL_RC" ] && ! grep -q "JOBRADAR_DIR" "$SHELL_RC" 2>/dev/null; then
  {
    echo ""
    echo "# JobRadar"
    echo "export JOBRADAR_DIR=\"$INSTALL_DIR\""
    echo "export PATH=\"$VENV/bin:\$PATH\""
  } >> "$SHELL_RC"
  echo "✅ Added jobradar to PATH in $SHELL_RC (reload shell or run: source $SHELL_RC)"
fi

export PATH="$VENV/bin:$PATH"
export JOBRADAR_DIR="$INSTALL_DIR"

# ── Step 5: Restart OpenClaw gateway (if OpenClaw is installed) ─────
if command -v openclaw >/dev/null 2>&1; then
  echo "🦞 OpenClaw detected — restarting gateway …"
  openclaw gateway restart 2>/dev/null || true
  sleep 3
  if openclaw skills list 2>/dev/null | grep -q jobradar; then
    echo "✅ JobRadar skill active in OpenClaw"
  else
    echo "⚠  Skill not yet visible — try: openclaw gateway restart"
  fi
fi

# ── Step 6: Summary ─────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ JobRadar installed!"
echo ""
echo "📂 Location : $INSTALL_DIR"
echo ""
echo "🚀 Quick start (CLI):"
echo "   jobradar init                          # interactive setup"
echo "   jobradar run --cv <url-or-path>        # run with your CV"
echo "   jobradar report --publish              # publish HTML report"
echo ""
echo "🤖 Quick start (OpenClaw / Claude):"
echo "   Just say: 'Find me jobs. My CV: <url-or-path>'"
echo "   The agent handles setup, scoring, and report automatically."
echo ""
echo "📄 CV formats accepted:"
echo "   • URL  : https://github.com/you/repo/blob/main/cv.md"
echo "   • File : /path/to/cv.pdf  or  ./cv/cv.md"
echo "   • Paste: jobradar init  (choose 'paste text' option)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
