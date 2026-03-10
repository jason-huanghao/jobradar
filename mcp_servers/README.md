# MCP Servers

This directory contains launcher scripts for MCP (Model Context Protocol) servers
used by the JobRadar agent.

## StepStone

```bash
# Install mcp-stepstone
pip install mcp-stepstone

# Or run directly
python stepstone_launcher.sh
```

## LinkedIn

Two adapters available:

### stickerdaniel (browser-based)
```bash
uvx linkedin-scraper-mcp --login
```

### rayyan (API-based)
Requires LinkedIn OAuth credentials in `.env`:
```
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
```

## Adding New MCP Servers

1. Create a launcher script in this directory
2. Add source config in `config.yaml` under `sources:`
3. Implement adapter in `src/sources/`
