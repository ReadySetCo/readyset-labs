"""
API Metrics Tracker - Tracks usage and costs of external APIs.
Provides real-time visibility into Gemini Vision, Firecrawl, Apify calls.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading

# Thread-safe singleton for metrics
_lock = threading.Lock()
_metrics: Dict[str, Any] = {
    "gemini_vision": {
        "video_calls": 0,
        "image_calls": 0,
        "text_calls": 0,
        "total_video_seconds": 0,
        "total_images": 0,
        "estimated_cost_usd": 0.0,
        "calls": []  # Recent calls with details
    },
    "firecrawl": {
        "scrape_calls": 0,
        "pages_scraped": 0,
        "estimated_cost_usd": 0.0,
        "calls": []
    },
    "apify": {
        "actor_runs": 0,
        "estimated_cost_usd": 0.0,
        "calls": []
    },
    "llm": {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "calls": []
    },
    "session_id": None,
    "started_at": None,
    "last_updated": None
}

# Cost estimates (approximate)
COSTS = {
    "gemini_video_per_second": 0.00025,  # $0.00025/sec
    "gemini_image_per_call": 0.001,       # $0.001/image
    "gemini_text_per_1k_input": 0.00025,  # $0.00025/1K input tokens
    "gemini_text_per_1k_output": 0.0005,  # $0.0005/1K output tokens
    "firecrawl_per_page": 0.001,          # $0.001/page
    "apify_per_result": 0.0005,           # $0.0005/result (varies by actor)
}


def start_session(session_id: int):
    """Start tracking a new session."""
    global _metrics
    with _lock:
        _metrics = {
            "gemini_vision": {"video_calls": 0, "image_calls": 0, "text_calls": 0, 
                             "total_video_seconds": 0, "estimated_cost_usd": 0.0, "calls": []},
            "firecrawl": {"scrape_calls": 0, "pages_scraped": 0, "estimated_cost_usd": 0.0, "calls": []},
            "apify": {"actor_runs": 0, "estimated_cost_usd": 0.0, "calls": []},
            "llm": {"calls": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "calls": []},
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }


def log_gemini_video(video_name: str, duration_seconds: float, processing_time: float, success: bool):
    """Log a Gemini Vision video analysis call."""
    with _lock:
        cost = duration_seconds * COSTS["gemini_video_per_second"] + 0.02  # +base cost
        _metrics["gemini_vision"]["video_calls"] += 1
        _metrics["gemini_vision"]["total_video_seconds"] += duration_seconds
        _metrics["gemini_vision"]["estimated_cost_usd"] += cost
        _metrics["gemini_vision"]["calls"].append({
            "type": "video",
            "file": video_name,
            "duration_sec": duration_seconds,
            "processing_time_sec": processing_time,
            "cost_usd": cost,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 50 calls
        _metrics["gemini_vision"]["calls"] = _metrics["gemini_vision"]["calls"][-50:]
        _metrics["last_updated"] = datetime.now().isoformat()


def log_gemini_image(image_name: str, processing_time: float, success: bool):
    """Log a Gemini Vision image analysis call."""
    with _lock:
        cost = COSTS["gemini_image_per_call"]
        _metrics["gemini_vision"]["image_calls"] += 1
        _metrics["gemini_vision"]["estimated_cost_usd"] += cost
        _metrics["gemini_vision"]["calls"].append({
            "type": "image",
            "file": image_name,
            "processing_time_sec": processing_time,
            "cost_usd": cost,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        _metrics["gemini_vision"]["calls"] = _metrics["gemini_vision"]["calls"][-50:]
        _metrics["last_updated"] = datetime.now().isoformat()


def log_llm_call(purpose: str, input_tokens: int = 0, output_tokens: int = 0):
    """Log a text LLM call."""
    with _lock:
        cost = (input_tokens / 1000 * COSTS["gemini_text_per_1k_input"]) + \
               (output_tokens / 1000 * COSTS["gemini_text_per_1k_output"])
        _metrics["llm"]["calls"] += 1
        _metrics["llm"]["input_tokens"] += input_tokens
        _metrics["llm"]["output_tokens"] += output_tokens
        _metrics["llm"]["estimated_cost_usd"] += cost
        _metrics["last_updated"] = datetime.now().isoformat()


def log_firecrawl_call(url: str, pages_scraped: int, success: bool):
    """Log a Firecrawl scraping call."""
    with _lock:
        cost = pages_scraped * COSTS["firecrawl_per_page"]
        _metrics["firecrawl"]["scrape_calls"] += 1
        _metrics["firecrawl"]["pages_scraped"] += pages_scraped
        _metrics["firecrawl"]["estimated_cost_usd"] += cost
        _metrics["firecrawl"]["calls"].append({
            "url": url[:100],
            "pages": pages_scraped,
            "cost_usd": cost,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        _metrics["firecrawl"]["calls"] = _metrics["firecrawl"]["calls"][-50:]
        _metrics["last_updated"] = datetime.now().isoformat()


def log_apify_call(actor_name: str, results_count: int, success: bool):
    """Log an Apify actor run."""
    with _lock:
        cost = results_count * COSTS["apify_per_result"]
        _metrics["apify"]["actor_runs"] += 1
        _metrics["apify"]["estimated_cost_usd"] += cost
        _metrics["apify"]["calls"].append({
            "actor": actor_name,
            "results": results_count,
            "cost_usd": cost,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        _metrics["apify"]["calls"] = _metrics["apify"]["calls"][-50:]
        _metrics["last_updated"] = datetime.now().isoformat()


def get_metrics() -> Dict[str, Any]:
    """Get current session metrics."""
    with _lock:
        return _metrics.copy()


def get_total_cost() -> float:
    """Get total estimated cost for current session."""
    with _lock:
        return (
            _metrics["gemini_vision"]["estimated_cost_usd"] +
            _metrics["firecrawl"]["estimated_cost_usd"] +
            _metrics["apify"]["estimated_cost_usd"] +
            _metrics["llm"]["estimated_cost_usd"]
        )


def get_summary() -> Dict[str, Any]:
    """Get a summary of API usage."""
    with _lock:
        return {
            "session_id": _metrics["session_id"],
            "started_at": _metrics["started_at"],
            "last_updated": _metrics["last_updated"],
            "gemini_vision": {
                "videos_analyzed": _metrics["gemini_vision"]["video_calls"],
                "images_analyzed": _metrics["gemini_vision"]["image_calls"],
                "total_video_seconds": _metrics["gemini_vision"]["total_video_seconds"],
                "cost_usd": round(_metrics["gemini_vision"]["estimated_cost_usd"], 3)
            },
            "firecrawl": {
                "pages_scraped": _metrics["firecrawl"]["pages_scraped"],
                "cost_usd": round(_metrics["firecrawl"]["estimated_cost_usd"], 3)
            },
            "apify": {
                "actor_runs": _metrics["apify"]["actor_runs"],
                "cost_usd": round(_metrics["apify"]["estimated_cost_usd"], 3)
            },
            "llm": {
                "calls": _metrics["llm"]["calls"],
                "tokens": _metrics["llm"]["input_tokens"] + _metrics["llm"]["output_tokens"],
                "cost_usd": round(_metrics["llm"]["estimated_cost_usd"], 3)
            },
            "total_estimated_cost_usd": round(get_total_cost(), 3)
        }


def print_summary():
    """Print a formatted summary to console."""
    s = get_summary()
    print("\n" + "="*60)
    print(f"📊 API METRICS - Session {s['session_id']}")
    print("="*60)
    print(f"  Started: {s['started_at']}")
    print(f"  Last update: {s['last_updated']}")
    print()
    print(f"  🎥 Gemini Vision:")
    print(f"     Videos: {s['gemini_vision']['videos_analyzed']} ({s['gemini_vision']['total_video_seconds']:.0f}s total)")
    print(f"     Images: {s['gemini_vision']['images_analyzed']}")
    print(f"     Cost: ${s['gemini_vision']['cost_usd']:.3f}")
    print()
    print(f"  🔥 Firecrawl:")
    print(f"     Pages: {s['firecrawl']['pages_scraped']}")
    print(f"     Cost: ${s['firecrawl']['cost_usd']:.3f}")
    print()
    print(f"  🐝 Apify:")
    print(f"     Runs: {s['apify']['actor_runs']}")
    print(f"     Cost: ${s['apify']['cost_usd']:.3f}")
    print()
    print(f"  🤖 LLM Calls: {s['llm']['calls']} ({s['llm']['tokens']:,} tokens)")
    print(f"     Cost: ${s['llm']['cost_usd']:.3f}")
    print()
    print(f"  💰 TOTAL ESTIMATED COST: ${s['total_estimated_cost_usd']:.3f}")
    print("="*60 + "\n")
