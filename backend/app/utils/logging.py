"""
Session logging utilities - Shared between routers and services.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict


# In-memory log storage per session
_session_logs: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
_session_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
    "api_calls": defaultdict(int),
    "api_errors": defaultdict(list),
    "rate_limits": defaultdict(int),
    "quota_warnings": [],
    "total_items_scraped": 0
})
MAX_LOGS_PER_SESSION = 500


def add_session_log(
    session_id: int, 
    message: str, 
    level: str = "info", 
    source: str = None, 
    details: Dict = None
):
    """Add a log entry for a research session."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "source": source,
        "details": details
    }
    _session_logs[session_id].append(log_entry)
    # Keep only last N logs
    if len(_session_logs[session_id]) > MAX_LOGS_PER_SESSION:
        _session_logs[session_id] = _session_logs[session_id][-MAX_LOGS_PER_SESSION:]


def get_session_logs(session_id: int) -> List[Dict[str, Any]]:
    """Get logs for a session."""
    return _session_logs.get(session_id, [])


def clear_session_logs(session_id: int):
    """Clear logs for a session."""
    if session_id in _session_logs:
        del _session_logs[session_id]
    if session_id in _session_stats:
        del _session_stats[session_id]


def track_api_call(session_id: int, api_name: str, success: bool = True, error: str = None):
    """Track an API call for quota/error monitoring."""
    stats = _session_stats[session_id]
    stats["api_calls"][api_name] += 1
    if not success and error:
        stats["api_errors"][api_name].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error
        })


def track_rate_limit(session_id: int, api_name: str):
    """Track when we hit a rate limit."""
    stats = _session_stats[session_id]
    stats["rate_limits"][api_name] += 1
    if stats["rate_limits"][api_name] >= 3:
        warning = f"{api_name} hit rate limit {stats['rate_limits'][api_name]} times - may be approaching quota"
        if warning not in stats["quota_warnings"]:
            stats["quota_warnings"].append(warning)


def track_items_scraped(session_id: int, count: int):
    """Track total items scraped."""
    _session_stats[session_id]["total_items_scraped"] += count


def get_session_stats(session_id: int) -> Dict[str, Any]:
    """Get stats summary for a session."""
    stats = _session_stats.get(session_id, {})
    return {
        "api_calls": dict(stats.get("api_calls", {})),
        "api_errors": {k: len(v) for k, v in stats.get("api_errors", {}).items()},
        "rate_limits": dict(stats.get("rate_limits", {})),
        "quota_warnings": stats.get("quota_warnings", []),
        "total_items_scraped": stats.get("total_items_scraped", 0)
    }
