<div align="center">

# Health Check Ai MCP

**MCP server for health check ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-health-check-ai-mcp)](https://pypi.org/project/meok-health-check-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Health Check Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `check_endpoint` | Check if a URL endpoint is responding. Returns status code, latency, headers, an |
| `batch_check` | Check multiple URLs (comma-separated). Returns status for each with summary stat |
| `get_uptime_report` | Get uptime report for a monitored URL based on check history, including availabi |
| `configure_monitor` | Configure a URL monitor with thresholds for alerting and tracking. |

## Installation

```bash
pip install meok-health-check-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "health-check-ai": {
      "command": "python",
      "args": ["-m", "meok_health_check_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 4 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
