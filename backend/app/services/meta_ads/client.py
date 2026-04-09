# -*- coding: utf-8 -*-
"""
Meta Ads API Client - Fetch ad performance data.

Provides methods to:
- Get account-level insights (spend, impressions, ROAS)
- Get ad-level performance breakdown
- Get creative analysis with performance data
"""

import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class MetaAdsClient:
    """Client for Meta (Facebook) Marketing API."""
    
    BASE_URL = "https://graph.facebook.com/v24.0"
    
    # Common insight metrics
    DEFAULT_METRICS = [
        "impressions",
        "reach",
        "clicks",
        "spend",
        "cpc",
        "cpm",
        "ctr",
        "frequency",
        "actions",
        "action_values",
        "purchase_roas",
        "cost_per_action_type"
    ]
    
    # Ad-level fields
    AD_FIELDS = [
        "id",
        "name",
        "status",
        "effective_status",
        "creative",
        "adset_id",
        "campaign_id",
        "created_time",
        "updated_time"
    ]
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Graph API."""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    async def get_account_insights(
        self,
        ad_account_id: str,
        date_preset: str = "last_30d",
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get account-level performance insights.
        
        Args:
            ad_account_id: Ad account ID (with or without 'act_' prefix)
            date_preset: Time range (last_7d, last_14d, last_30d, last_90d, etc.)
            metrics: List of metrics to fetch (uses defaults if not specified)
            
        Returns:
            Dict with performance metrics
        """
        # Ensure act_ prefix
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        
        metrics = metrics or self.DEFAULT_METRICS
        
        params = {
            "fields": ",".join(metrics),
            "date_preset": date_preset,
            "level": "account"
        }
        
        data = await self._request(f"{ad_account_id}/insights", params)
        
        if data.get("data"):
            return data["data"][0]  # Account level returns single record
        return {}
    
    async def get_campaign_insights(
        self,
        ad_account_id: str,
        date_preset: str = "last_30d",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get campaign-level performance breakdown.
        
        Args:
            ad_account_id: Ad account ID
            date_preset: Time range
            limit: Max campaigns to return
            
        Returns:
            List of campaign performance dicts
        """
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        
        params = {
            "fields": ",".join(self.DEFAULT_METRICS + ["campaign_name", "campaign_id"]),
            "date_preset": date_preset,
            "level": "campaign",
            "limit": limit
        }
        
        data = await self._request(f"{ad_account_id}/insights", params)
        return data.get("data", [])
    
    async def get_ad_insights(
        self,
        ad_account_id: str,
        date_preset: str = "last_30d",
        limit: int = 100,
        status_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ad-level performance with creative info.
        
        Args:
            ad_account_id: Ad account ID
            date_preset: Time range
            limit: Max ads to return
            status_filter: Filter by status (ACTIVE, PAUSED, etc.)
            
        Returns:
            List of ad performance dicts with creative details
        """
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        
        params = {
            "fields": ",".join(self.DEFAULT_METRICS + ["ad_id", "ad_name"]),
            "date_preset": date_preset,
            "level": "ad",
            "limit": limit
        }
        
        if status_filter:
            params["filtering"] = f'[{{"field":"effective_status","operator":"IN","value":{status_filter}}}]'
        
        data = await self._request(f"{ad_account_id}/insights", params)
        return data.get("data", [])
    
    async def get_ads_with_creative(
        self,
        ad_account_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get ads with their creative details.
        
        Args:
            ad_account_id: Ad account ID
            limit: Max ads to return
            
        Returns:
            List of ads with creative info
        """
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"
        
        params = {
            "fields": ",".join(self.AD_FIELDS) + ",insights{" + ",".join(self.DEFAULT_METRICS) + "}",
            "limit": limit
        }
        
        data = await self._request(f"{ad_account_id}/ads", params)
        return data.get("data", [])
    
    async def get_creative_details(
        self,
        creative_id: str
    ) -> Dict[str, Any]:
        """
        Get full creative details for an ad.
        
        Args:
            creative_id: Creative ID
            
        Returns:
            Dict with creative details (thumbnail, body, title, video, etc.)
        """
        params = {
            "fields": "id,name,title,body,image_url,thumbnail_url,video_id,object_story_spec,effective_object_story_id"
        }
        
        return await self._request(creative_id, params)
    
    async def get_top_performing_ads(
        self,
        ad_account_id: str,
        metric: str = "purchase_roas",
        date_preset: str = "last_30d",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get top performing ads sorted by a specific metric.
        
        Args:
            ad_account_id: Ad account ID
            metric: Metric to sort by (purchase_roas, ctr, cpc, etc.)
            date_preset: Time range
            limit: Max ads to return
            
        Returns:
            List of top performing ads
        """
        ads = await self.get_ad_insights(ad_account_id, date_preset, limit * 2)
        
        # Sort by metric (handle nested action values)
        def get_metric_value(ad: Dict) -> float:
            if metric == "purchase_roas":
                roas = ad.get("purchase_roas", [])
                if roas and isinstance(roas, list):
                    return float(roas[0].get("value", 0))
                return 0
            return float(ad.get(metric, 0))
        
        sorted_ads = sorted(ads, key=get_metric_value, reverse=True)
        return sorted_ads[:limit]
    
    async def compare_ad_performance(
        self,
        ad_ids: List[str],
        date_preset: str = "last_30d"
    ) -> List[Dict[str, Any]]:
        """
        Compare performance across specific ads.
        
        Args:
            ad_ids: List of ad IDs to compare
            date_preset: Time range
            
        Returns:
            List of ad performance dicts for comparison
        """
        results = []
        
        for ad_id in ad_ids:
            try:
                params = {
                    "fields": ",".join(self.DEFAULT_METRICS + ["ad_name"]),
                    "date_preset": date_preset
                }
                data = await self._request(f"{ad_id}/insights", params)
                if data.get("data"):
                    results.append({
                        "ad_id": ad_id,
                        **data["data"][0]
                    })
            except Exception as e:
                print(f"    [Meta] Error fetching ad {ad_id}: {e}")
        
        return results


# Factory function
def get_meta_client(access_token: str) -> MetaAdsClient:
    """Create a Meta Ads client instance."""
    return MetaAdsClient(access_token)
