# Health Check Ai

> By [MEOK AI Labs](https://meok.ai) — MEOK AI Labs — HTTP endpoint health monitoring, SSL checks, and uptime tracking.

HTTP endpoint health monitoring and status checking. — MEOK AI Labs.

## Installation

```bash
pip install health-check-ai-mcp
```

## Usage

```bash
# Run standalone
python server.py

# Or via MCP
mcp install health-check-ai-mcp
```

## Tools

### `check_endpoint`
Check if a URL endpoint is responding. Returns status code, latency, headers, and health assessment.

**Parameters:**
- `url` (str)
- `timeout` (int)
- `expected_status` (int)

### `batch_check`
Check multiple URLs (comma-separated). Returns status for each with summary statistics.

**Parameters:**
- `urls` (str)
- `timeout` (int)

### `get_uptime_report`
Get uptime report for a monitored URL based on check history, including availability and latency trends.

**Parameters:**
- `url` (str)

### `configure_monitor`
Configure a URL monitor with thresholds for alerting and tracking.

**Parameters:**
- `url` (str)
- `name` (str)
- `expected_status` (int)
- `alert_threshold_ms` (int)


## Authentication

Free tier: 15 calls/day. Upgrade at [meok.ai/pricing](https://meok.ai/pricing) for unlimited access.

## Links

- **Website**: [meok.ai](https://meok.ai)
- **GitHub**: [CSOAI-ORG/health-check-ai-mcp](https://github.com/CSOAI-ORG/health-check-ai-mcp)
- **PyPI**: [pypi.org/project/health-check-ai-mcp](https://pypi.org/project/health-check-ai-mcp/)

## License

MIT — MEOK AI Labs
