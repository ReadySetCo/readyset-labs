# -*- coding: utf-8 -*-
"""
Meta Ads Integration Service

Connect to Meta (Facebook) Ads API to retrieve real performance data.
This enables data-driven creative strategy based on actual ad performance.

Features:
- OAuth flow for account connection
- Insights API for performance metrics
- Ad-level breakdown for creative analysis
- Automated performance reports

See docs/11_meta_ads_integration.md for full implementation plan.
"""

from .client import MetaAdsClient, get_meta_client
from .oauth import MetaOAuthService, get_oauth_service

__all__ = [
    "MetaAdsClient",
    "get_meta_client",
    "MetaOAuthService", 
    "get_oauth_service"
]
