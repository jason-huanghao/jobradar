#!/usr/bin/env bash
# StepStone MCP server launcher
# Requires: pip install mcp-stepstone

set -euo pipefail

echo "Starting StepStone MCP server..."
python -m mcp_stepstone.server
