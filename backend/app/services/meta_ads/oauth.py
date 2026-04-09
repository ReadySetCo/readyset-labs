# -*- coding: utf-8 -*-
"""
Meta OAuth Service - Handle OAuth flow for Meta Ads API.

Flow:
1. User clicks "Connect Meta Ads"
2. Redirect to Facebook OAuth with required permissions
3. User grants access
4. Callback receives code
5. Exchange code for access token
6. Store encrypted token in database
"""

import os
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlencode
from datetime import datetime, timedelta, timezone

from ...config import settings


class MetaOAuthService:
    """Handle Meta (Facebook) OAuth authentication flow."""
    
    # OAuth endpoints
    AUTH_URL = "https://www.facebook.com/v24.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v24.0/oauth/access_token"
    DEBUG_TOKEN_URL = "https://graph.facebook.com/debug_token"
    
    # Required permissions for ads access
    REQUIRED_SCOPES = [
        "ads_read",           # Read ad performance data
        "read_insights",      # Access account insights
        "business_management" # For agency multi-account (optional)
    ]
    
    def __init__(self):
        self.app_id = settings.META_APP_ID if hasattr(settings, 'META_APP_ID') else os.getenv("META_APP_ID")
        self.app_secret = settings.META_APP_SECRET if hasattr(settings, 'META_APP_SECRET') else os.getenv("META_APP_SECRET")
        self.redirect_uri = settings.META_REDIRECT_URI if hasattr(settings, 'META_REDIRECT_URI') else os.getenv("META_REDIRECT_URI", "http://localhost:8000/api/meta/auth/callback")
        
        self._is_configured = bool(self.app_id and self.app_secret)
    
    @property
    def is_available(self) -> bool:
        """Check if Meta OAuth is properly configured."""
        return self._is_configured
    
    def get_authorization_url(self, state: str = "") -> str:
        """
        Generate the OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Full authorization URL to redirect user to
        """
        if not self.is_available:
            raise ValueError("Meta OAuth not configured. Set META_APP_ID and META_APP_SECRET.")
        
        params = {
            "client_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(self.REQUIRED_SCOPES),
            "response_type": "code",
            "state": state
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dict with access_token, token_type, expires_in
        """
        if not self.is_available:
            raise ValueError("Meta OAuth not configured")
        
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": self.redirect_uri,
            "code": code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.TOKEN_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate expiry time
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            return {
                "access_token": data.get("access_token"),
                "token_type": data.get("token_type", "bearer"),
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat()
            }
    
    async def exchange_for_long_lived_token(self, short_lived_token: str) -> Dict[str, Any]:
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Dict with long-lived access_token and expiry
        """
        if not self.is_available:
            raise ValueError("Meta OAuth not configured")
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.TOKEN_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            expires_in = data.get("expires_in", 5184000)  # Default 60 days
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            return {
                "access_token": data.get("access_token"),
                "token_type": "bearer",
                "expires_in": expires_in,
                "expires_at": expires_at.isoformat(),
                "is_long_lived": True
            }
    
    async def validate_token(self, access_token: str) -> Dict[str, Any]:
        """
        Validate and get info about an access token.
        
        Args:
            access_token: Token to validate
            
        Returns:
            Dict with token info (user_id, scopes, expires_at, etc.)
        """
        if not self.is_available:
            raise ValueError("Meta OAuth not configured")
        
        params = {
            "input_token": access_token,
            "access_token": f"{self.app_id}|{self.app_secret}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.DEBUG_TOKEN_URL, params=params)
            response.raise_for_status()
            
            data = response.json().get("data", {})
            
            return {
                "is_valid": data.get("is_valid", False),
                "user_id": data.get("user_id"),
                "app_id": data.get("app_id"),
                "scopes": data.get("scopes", []),
                "expires_at": datetime.fromtimestamp(data.get("expires_at", 0)).isoformat() if data.get("expires_at") else None,
                "data_access_expires_at": datetime.fromtimestamp(data.get("data_access_expires_at", 0)).isoformat() if data.get("data_access_expires_at") else None
            }
    
    async def get_ad_accounts(self, access_token: str) -> list:
        """
        Get list of ad accounts the user has access to.
        
        Args:
            access_token: Valid access token
            
        Returns:
            List of ad account dicts with id, name, currency, etc.
        """
        url = "https://graph.facebook.com/v24.0/me/adaccounts"
        params = {
            "access_token": access_token,
            "fields": "id,name,account_id,currency,timezone_name,account_status,business_name"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])


# Singleton instance
_oauth_service: Optional[MetaOAuthService] = None

def get_oauth_service() -> MetaOAuthService:
    """Get Meta OAuth service instance."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = MetaOAuthService()
    return _oauth_service
