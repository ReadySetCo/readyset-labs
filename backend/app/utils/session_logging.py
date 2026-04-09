"""
Session logging utilities - Shared between routers and services.
Enhanced with persistent file storage (Phase 7.5).
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path


# Configuration
LOGS_DIR = Path(__file__).parent.parent.parent / "logs" / "sessions"
MAX_LOGS_PER_SESSION = 1000
PERSIST_TO_FILE = True


# In-memory log storage per session (for real-time access)
_session_logs: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

# Phase progress storage
_session_progress: Dict[int, Dict[str, Any]] = {}


def _ensure_logs_dir():
    """Ensure the logs directory exists."""
    if PERSIST_TO_FILE:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _get_log_file_path(session_id: int) -> Path:
    """Get the log file path for a session."""
    return LOGS_DIR / f"session_{session_id}.jsonl"


def add_session_log(
    session_id: int, 
    message: str, 
    level: str = "info", 
    source: str = None, 
    details: Dict = None
):
    """
    Add a log entry for a research session.
    
    Logs are stored in memory for real-time access and persisted to file for durability.
    
    Args:
        session_id: Research session ID
        message: Log message
        level: Log level (info, success, warning, error)
        source: Source component (scraper name, analyzer, etc.)
        details: Additional structured data
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "level": level,
        "message": message,
        "source": source,
        "details": details
    }
    
    # Add to memory
    _session_logs[session_id].append(log_entry)
    
    # Keep only last N logs in memory
    if len(_session_logs[session_id]) > MAX_LOGS_PER_SESSION:
        _session_logs[session_id] = _session_logs[session_id][-MAX_LOGS_PER_SESSION:]
    
    # Persist to file
    if PERSIST_TO_FILE:
        try:
            _ensure_logs_dir()
            log_file = _get_log_file_path(session_id)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # Don't fail silently, but don't crash either
            print(f"[LOG] Failed to persist log: {e}")


def get_session_logs(session_id: int, from_file: bool = False) -> List[Dict[str, Any]]:
    """
    Get logs for a session.
    
    Args:
        session_id: Research session ID
        from_file: If True, load from file (useful after restart)
    
    Returns:
        List of log entries
    """
    if from_file and PERSIST_TO_FILE:
        return load_session_logs_from_file(session_id)
    return _session_logs.get(session_id, [])


def load_session_logs_from_file(session_id: int) -> List[Dict[str, Any]]:
    """Load logs from file for a session."""
    log_file = _get_log_file_path(session_id)
    if not log_file.exists():
        return []
    
    logs = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
    except Exception as e:
        print(f"[LOG] Failed to load logs from file: {e}")
    
    return logs


def clear_session_logs(session_id: int, delete_file: bool = False):
    """
    Clear logs for a session.
    
    Args:
        session_id: Research session ID
        delete_file: If True, also delete the log file
    """
    if session_id in _session_logs:
        del _session_logs[session_id]
    
    if delete_file and PERSIST_TO_FILE:
        log_file = _get_log_file_path(session_id)
        if log_file.exists():
            log_file.unlink()


def get_logs_by_level(session_id: int, level: str) -> List[Dict[str, Any]]:
    """Get logs filtered by level."""
    return [log for log in get_session_logs(session_id) if log.get("level") == level]


def get_logs_by_source(session_id: int, source: str) -> List[Dict[str, Any]]:
    """Get logs filtered by source."""
    return [log for log in get_session_logs(session_id) if log.get("source") == source]


def search_logs(session_id: int, query: str) -> List[Dict[str, Any]]:
    """Search logs by message content."""
    query_lower = query.lower()
    return [
        log for log in get_session_logs(session_id) 
        if query_lower in log.get("message", "").lower()
    ]


def get_error_summary(session_id: int) -> Dict[str, Any]:
    """Get a summary of errors and warnings for a session."""
    logs = get_session_logs(session_id)
    
    errors = [log for log in logs if log.get("level") == "error"]
    warnings = [log for log in logs if log.get("level") == "warning"]
    
    return {
        "total_logs": len(logs),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors[-10:],  # Last 10 errors
        "warnings": warnings[-10:],  # Last 10 warnings
    }


def list_session_log_files() -> List[Dict[str, Any]]:
    """List all session log files with metadata."""
    if not LOGS_DIR.exists():
        return []
    
    sessions = []
    for log_file in LOGS_DIR.glob("session_*.jsonl"):
        try:
            session_id = int(log_file.stem.replace("session_", ""))
            stat = log_file.stat()
            sessions.append({
                "session_id": session_id,
                "file_path": str(log_file),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "line_count": sum(1 for _ in open(log_file, "r", encoding="utf-8"))
            })
        except Exception as e:
            continue
    
    return sorted(sessions, key=lambda x: x["session_id"], reverse=True)


# =============================================================================
# PHASE PROGRESS TRACKING
# =============================================================================

def set_phase_progress(
    session_id: int,
    phase: str,
    step: int,
    total_steps: int,
    description: str
):
    """
    Update phase progress for a session.
    
    Args:
        session_id: Research session ID
        phase: Current phase name (brand_dna, discovery, scraping, etc.)
        step: Current step within the phase (1-indexed)
        total_steps: Total steps in this phase
        description: Human-readable description of current step
    """
    progress = {
        "phase": phase,
        "step": step,
        "total_steps": total_steps,
        "description": description,
        "percent": int((step / total_steps) * 100) if total_steps > 0 else 0,
        "updated_at": datetime.now(timezone.utc).isoformat() + "Z"
    }
    
    _session_progress[session_id] = progress
    
    # Also log the progress update
    add_session_log(
        session_id=session_id,
        message=f"[{phase}] {step}/{total_steps}: {description}",
        level="info",
        source="progress",
        details=progress
    )


def get_phase_progress(session_id: int) -> Dict[str, Any]:
    """Get current phase progress for a session."""
    return _session_progress.get(session_id, {
        "phase": "initializing",
        "step": 0,
        "total_steps": 0,
        "description": "Starting research...",
        "percent": 0,
        "updated_at": None
    })


def clear_phase_progress(session_id: int):
    """Clear phase progress for a session."""
    if session_id in _session_progress:
        del _session_progress[session_id]


# =============================================================================
# CONVENIENCE FUNCTIONS FOR COMMON LOG TYPES
# =============================================================================

def log_scraper_start(session_id: int, scraper: str, queries: List[str] = None):
    """Log scraper starting."""
    add_session_log(
        session_id=session_id,
        message=f"Starting {scraper} scraper",
        level="info",
        source=scraper,
        details={"queries": queries[:3] if queries else None}
    )


def log_scraper_result(session_id: int, scraper: str, count: int, elapsed: float = None):
    """Log scraper completion."""
    add_session_log(
        session_id=session_id,
        message=f"{scraper}: {count} items collected" + (f" ({elapsed:.1f}s)" if elapsed else ""),
        level="success" if count > 0 else "warning",
        source=scraper,
        details={"count": count, "elapsed_seconds": elapsed}
    )


def log_error(session_id: int, source: str, error: str, details: Dict = None):
    """Log an error."""
    add_session_log(
        session_id=session_id,
        message=f"Error in {source}: {error}",
        level="error",
        source=source,
        details=details
    )


def log_analysis_complete(session_id: int, analyzer: str, summary: str = None):
    """Log analysis completion."""
    add_session_log(
        session_id=session_id,
        message=f"{analyzer} analysis complete" + (f": {summary}" if summary else ""),
        level="success",
        source=analyzer
    )

