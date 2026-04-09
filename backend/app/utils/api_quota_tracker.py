"""
API Quota Tracker - Monitors API usage and detects quota exhaustion.
Provides clear warnings when APIs fail due to quota limits.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import httpx


class APIStatus(Enum):
    """API status states."""
    OK = "ok"
    LOW_QUOTA = "low_quota"  # < 20% remaining
    EXHAUSTED = "exhausted"  # No quota left
    ERROR = "error"  # API error (not quota related)
    UNKNOWN = "unknown"


@dataclass
class APIQuotaInfo:
    """Information about API quota."""
    name: str
    status: APIStatus = APIStatus.UNKNOWN
    remaining: Optional[float] = None  # Percentage or absolute value
    limit: Optional[float] = None
    last_check: Optional[datetime] = None
    last_error: Optional[str] = None
    requests_made: int = 0
    requests_failed: int = 0


class APIQuotaTracker:
    """
    Tracks API quota usage across all services.
    Provides warnings when quota is low or exhausted.
    """
    
    def __init__(self):
        self._apis: Dict[str, APIQuotaInfo] = {
            "firecrawl": APIQuotaInfo(name="Firecrawl"),
            "apify": APIQuotaInfo(name="Apify"),
            "gemini": APIQuotaInfo(name="Gemini"),
            "openai": APIQuotaInfo(name="OpenAI"),
        }
        self._session_errors: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
    
    def record_request(self, api_name: str, success: bool, error_msg: Optional[str] = None):
        """Record an API request result."""
        if api_name not in self._apis:
            self._apis[api_name] = APIQuotaInfo(name=api_name)
        
        info = self._apis[api_name]
        info.requests_made += 1
        
        if not success:
            info.requests_failed += 1
            info.last_error = error_msg
            
            # Detect quota exhaustion from error messages
            if error_msg:
                error_lower = error_msg.lower()
                quota_indicators = [
                    "quota", "rate limit", "429", "too many requests",
                    "insufficient credits", "billing", "exceeded",
                    "limit reached", "no credits", "exhausted"
                ]
                if any(ind in error_lower for ind in quota_indicators):
                    info.status = APIStatus.EXHAUSTED
                    self._log_quota_error(api_name, error_msg)
    
    def _log_quota_error(self, api_name: str, error_msg: str):
        """Log a quota error for session summary."""
        self._session_errors.append({
            "api": api_name,
            "error": error_msg,
            "timestamp": datetime.now().isoformat(),
            "type": "quota_exhausted"
        })
        print(f"\n{'='*60}")
        print(f"⚠️  API QUOTA WARNING: {api_name.upper()}")
        print(f"{'='*60}")
        print(f"Error: {error_msg[:100]}")
        print(f"Some features may not work until quota is restored.")
        print(f"{'='*60}\n")
    
    def update_status(self, api_name: str, status: APIStatus, remaining: Optional[float] = None):
        """Update API status directly."""
        if api_name not in self._apis:
            self._apis[api_name] = APIQuotaInfo(name=api_name)
        
        info = self._apis[api_name]
        info.status = status
        info.remaining = remaining
        info.last_check = datetime.now()
    
    def get_status(self, api_name: str) -> APIQuotaInfo:
        """Get status for a specific API."""
        return self._apis.get(api_name, APIQuotaInfo(name=api_name))
    
    def get_all_statuses(self) -> Dict[str, APIQuotaInfo]:
        """Get status for all APIs."""
        return self._apis.copy()
    
    def get_session_errors(self) -> List[Dict[str, Any]]:
        """Get all quota errors from this session."""
        return self._session_errors.copy()
    
    def has_quota_errors(self) -> bool:
        """Check if any quota errors occurred."""
        return len(self._session_errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of API status for logging."""
        summary = {
            "apis": {},
            "quota_errors": len(self._session_errors),
            "errors": self._session_errors[-5:] if self._session_errors else []  # Last 5 errors
        }
        
        for name, info in self._apis.items():
            summary["apis"][name] = {
                "status": info.status.value,
                "requests": info.requests_made,
                "failed": info.requests_failed,
                "last_error": info.last_error[:100] if info.last_error else None
            }
        
        return summary
    
    def print_summary(self):
        """Print a human-readable summary."""
        print("\n" + "="*60)
        print("  API STATUS SUMMARY")
        print("="*60)
        
        for name, info in self._apis.items():
            status_icon = {
                APIStatus.OK: "✅",
                APIStatus.LOW_QUOTA: "⚠️",
                APIStatus.EXHAUSTED: "❌",
                APIStatus.ERROR: "🔴",
                APIStatus.UNKNOWN: "❓"
            }.get(info.status, "❓")
            
            print(f"  {status_icon} {name}: {info.status.value} ({info.requests_made} requests, {info.requests_failed} failed)")
            if info.last_error and info.status in [APIStatus.EXHAUSTED, APIStatus.ERROR]:
                print(f"      Last error: {info.last_error[:60]}...")
        
        if self._session_errors:
            print("\n  ⚠️  QUOTA WARNINGS:")
            for err in self._session_errors[-3:]:
                print(f"      - {err['api']}: {err['error'][:50]}...")
        
        print("="*60 + "\n")


# Global singleton instance
_tracker: Optional[APIQuotaTracker] = None


def get_quota_tracker() -> APIQuotaTracker:
    """Get global quota tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = APIQuotaTracker()
    return _tracker


async def check_apify_quota() -> Dict[str, Any]:
    """
    Check Apify account quota/balance.
    Returns usage info or error.
    """
    from ..config import settings
    
    if not settings.APIFY_API_TOKEN:
        return {"status": "no_token", "error": "No API token configured"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get account info
            resp = await client.get(
                f"https://api.apify.com/v2/users/me?token={settings.APIFY_API_TOKEN}"
            )
            
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                plan = data.get("plan", {})
                usage = data.get("currentBillingPeriod", {})
                
                # Calculate remaining
                monthly_usage = usage.get("usageUsd", 0)
                plan_limit = plan.get("monthlyUsageCreditsUsd", 0)
                remaining = plan_limit - monthly_usage if plan_limit else None
                
                tracker = get_quota_tracker()
                if remaining is not None and remaining <= 0:
                    tracker.update_status("apify", APIStatus.EXHAUSTED, 0)
                elif remaining is not None and remaining < 5:
                    tracker.update_status("apify", APIStatus.LOW_QUOTA, remaining)
                else:
                    tracker.update_status("apify", APIStatus.OK, remaining)
                
                return {
                    "status": "ok",
                    "usage_usd": monthly_usage,
                    "remaining_usd": remaining,
                    "plan": plan.get("name", "unknown")
                }
            elif resp.status_code == 401:
                return {"status": "invalid_token", "error": "Invalid API token"}
            else:
                return {"status": "error", "error": f"HTTP {resp.status_code}"}
                
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_firecrawl_quota() -> Dict[str, Any]:
    """
    Check Firecrawl usage (no direct quota API, but we can check if it works).
    """
    from ..config import settings
    
    if not settings.FIRECRAWL_API_KEY:
        return {"status": "no_token", "error": "No API key configured"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try a minimal request to check if API works
            resp = await client.post(
                f"{settings.FIRECRAWL_BASE_URL}/search",
                headers={
                    "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"query": "test", "limit": 1}
            )
            
            tracker = get_quota_tracker()
            
            if resp.status_code == 200:
                tracker.update_status("firecrawl", APIStatus.OK)
                return {"status": "ok"}
            elif resp.status_code == 402:
                tracker.update_status("firecrawl", APIStatus.EXHAUSTED)
                return {"status": "exhausted", "error": "Insufficient credits"}
            elif resp.status_code == 429:
                tracker.update_status("firecrawl", APIStatus.LOW_QUOTA)
                return {"status": "rate_limited", "error": "Rate limited"}
            else:
                return {"status": "error", "error": f"HTTP {resp.status_code}"}
                
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_all_quotas() -> Dict[str, Any]:
    """Check quota for all APIs."""
    results = {}
    
    # Check in parallel
    apify_task = check_apify_quota()
    firecrawl_task = check_firecrawl_quota()
    
    results["apify"] = await apify_task
    results["firecrawl"] = await firecrawl_task
    
    return results



