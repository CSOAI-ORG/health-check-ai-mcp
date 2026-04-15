#!/usr/bin/env python3
"""HTTP endpoint health monitoring and status checking. — MEOK AI Labs."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
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


@mcp.tool()
def check_endpoint(url: str, timeout: int = 5, expected_status: int = 200,
                    api_key: str = "") -> str:
    """Check if a URL endpoint is responding. Returns status code, latency, headers, and health assessment."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
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
    """Check multiple URLs (comma-separated). Returns status for each with summary statistics."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
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
    """Get uptime report for a monitored URL based on check history, including availability and latency trends."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
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
    """Configure a URL monitor with thresholds for alerting and tracking."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
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


if __name__ == "__main__":
    mcp.run()
