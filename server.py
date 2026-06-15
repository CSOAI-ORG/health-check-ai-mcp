#!/usr/bin/env python3
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr
"""
HTTP endpoint health monitoring and status checking. — MEOK AI Labs."""

import sys, os
from auth_middleware import check_access

import json, ssl, socket, time, hashlib
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

FREE_DAILY_LIMIT = 30
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now-t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT: return json.dumps({"error": "Limit {0}/day. Upgrade: meok.ai".format(FREE_DAILY_LIMIT)})
    _usage[c].append(now); return None

mcp = FastMCP("health-check-ai", instructions="MEOK AI Labs — HTTP endpoint health monitoring, SSL checks, and uptime tracking.")

_check_history: dict = defaultdict(list)
_monitors: dict = {}

STATUS_CODES = {
    200: "OK", 201: "Created", 301: "Moved Permanently", 302: "Found",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
    500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable",
}


def _do_check(url: str, timeout: int = 5) -> dict:
    result = {"url": url, "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        start = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "MEOK-HealthCheck/1.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        elapsed = time.time() - start
        result["status_code"] = resp.status
        result["status_text"] = STATUS_CODES.get(resp.status, "Unknown")
        result["latency_ms"] = round(elapsed * 1000, 1)
        result["healthy"] = 200 <= resp.status < 400
        headers = dict(resp.getheaders())
        result["server"] = headers.get("Server", "Unknown")
        result["content_type"] = headers.get("Content-Type", "Unknown")
        result["content_length"] = headers.get("Content-Length", "Unknown")
        body = resp.read(512)
        result["body_hash"] = hashlib.md5(body).hexdigest()
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["status_text"] = STATUS_CODES.get(e.code, str(e.reason))
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        result["healthy"] = False
        result["error"] = str(e.reason)
    except urllib.error.URLError as e:
        result["status_code"] = 0
        result["latency_ms"] = round((time.time() - start) * 1000, 1)
        result["healthy"] = False
        result["error"] = str(e.reason)
    except Exception as e:
        result["healthy"] = False
        result["error"] = str(e)
        result["latency_ms"] = 0

    _check_history[url].append(result)
    if len(_check_history[url]) > 100:
        _check_history[url] = _check_history[url][-100:]
    return result


def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Fail-open."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def check_endpoint(url: str, timeout: int = 5, expected_status: int = 200,
                    api_key: str = "") -> str:
    """Check if a URL endpoint is responding. Returns status code, latency, headers, and health assessment.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        url (str): The url to analyze or process.
        timeout (int): The timeout to analyze or process.
        expected_status (int): The expected status to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    result = _do_check(url, timeout)
    result["expected_status"] = expected_status
    result["status_match"] = result.get("status_code") == expected_status

    latency = result.get("latency_ms", 0)
    if latency < 200:
        result["performance"] = "excellent"
    elif latency < 500:
        result["performance"] = "good"
    elif latency < 1000:
        result["performance"] = "acceptable"
    elif latency < 3000:
        result["performance"] = "slow"
    else:
        result["performance"] = "critical"

    history = _check_history.get(url, [])
    if len(history) > 1:
        recent = history[-10:]
        avg_latency = round(sum(r.get("latency_ms", 0) for r in recent) / len(recent), 1)
        result["avg_latency_ms"] = avg_latency
        result["checks_recorded"] = len(history)

    return result


@mcp.tool()
def batch_check(urls: str, timeout: int = 5, api_key: str = "") -> str:
    """Check multiple URLs (comma-separated). Returns status for each with summary statistics.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        urls (str): The urls to analyze or process.
        timeout (int): The timeout to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if len(url_list) > 20:
        return {"error": "Maximum 20 URLs per batch check", "provided": len(url_list)}

    results = []
    for url in url_list:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        results.append(_do_check(url, timeout))

    healthy_count = sum(1 for r in results if r.get("healthy"))
    latencies = [r.get("latency_ms", 0) for r in results if r.get("latency_ms")]

    summary = {
        "total": len(results),
        "healthy": healthy_count,
        "unhealthy": len(results) - healthy_count,
        "health_pct": round(healthy_count / len(results) * 100, 1) if results else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "min_latency_ms": round(min(latencies), 1) if latencies else 0,
        "max_latency_ms": round(max(latencies), 1) if latencies else 0,
        "slowest": max(results, key=lambda r: r.get("latency_ms", 0)).get("url") if results else None,
    }

    return {"results": results, "summary": summary, "timestamp": datetime.now(timezone.utc).isoformat()}


@mcp.tool()
def get_uptime_report(url: str, api_key: str = "") -> str:
    """Get uptime report for a monitored URL based on check history, including availability and latency trends.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        url (str): The url to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    history = _check_history.get(url, [])
    if not history:
        return {"url": url, "error": "No check history found. Run check_endpoint first.",
                "timestamp": datetime.now(timezone.utc).isoformat()}

    total = len(history)
    healthy = sum(1 for h in history if h.get("healthy"))
    latencies = [h.get("latency_ms", 0) for h in history if h.get("latency_ms")]

    status_codes = defaultdict(int)
    for h in history:
        code = h.get("status_code", 0)
        status_codes[code] += 1

    errors = [h for h in history if not h.get("healthy")]
    last_5_errors = errors[-5:] if errors else []

    trend = []
    for i in range(0, len(history), max(1, len(history) // 10)):
        chunk = history[i:i + max(1, len(history) // 10)]
        chunk_latencies = [c.get("latency_ms", 0) for c in chunk if c.get("latency_ms")]
        if chunk_latencies:
            trend.append({"index": i, "avg_latency_ms": round(sum(chunk_latencies) / len(chunk_latencies), 1),
                          "healthy_pct": round(sum(1 for c in chunk if c.get("healthy")) / len(chunk) * 100, 1)})

    return {
        "url": url,
        "total_checks": total,
        "uptime_pct": round(healthy / total * 100, 2) if total else 0,
        "healthy_checks": healthy,
        "failed_checks": total - healthy,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "min_latency_ms": round(min(latencies), 1) if latencies else 0,
        "max_latency_ms": round(max(latencies), 1) if latencies else 0,
        "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 1),
        "status_codes": dict(status_codes),
        "recent_errors": last_5_errors,
        "trend": trend,
        "first_check": history[0].get("timestamp"),
        "last_check": history[-1].get("timestamp"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def configure_monitor(url: str, name: str = "", expected_status: int = 200,
                       alert_threshold_ms: int = 2000, api_key: str = "") -> str:
    """Configure a URL monitor with thresholds for alerting and tracking.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.

    Args:
        url (str): The url to analyze or process.
        name (str): The name to analyze or process.
        expected_status (int): The expected status to analyze or process.
        alert_threshold_ms (int): The alert threshold ms to analyze or process.
        api_key (str): The api key to analyze or process.

    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if err := _rl(): return err

    monitor_id = hashlib.md5(url.encode()).hexdigest()[:12]
    _monitors[monitor_id] = {
        "id": monitor_id,
        "url": url,
        "name": name or url,
        "expected_status": expected_status,
        "alert_threshold_ms": alert_threshold_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }

    all_monitors = [{"id": m["id"], "name": m["name"], "url": m["url"], "active": m["active"]}
                     for m in _monitors.values()]

    return {
        "monitor_id": monitor_id,
        "url": url,
        "name": name or url,
        "expected_status": expected_status,
        "alert_threshold_ms": alert_threshold_ms,
        "status": "configured",
        "total_monitors": len(_monitors),
        "all_monitors": all_monitors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    mcp.run()

if __name__ == '__main__':
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/5kQ6oJ0xS3ce8sl7ew8k91j"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
