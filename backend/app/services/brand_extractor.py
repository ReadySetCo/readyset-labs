"""
Brand Extractor - Extrae brand name correcto usando FB/IG y validación en Ad Library.

Flujo:
1. Extraer username de FB/IG URLs
2. Buscar en Ad Library con FB username → obtener page_id + display_name
3. Buscar con IG username → si mismo page_id → validado
4. Fallback ladder: FB → IG → input original
"""

import re
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
import httpx

from ..config import settings
from .adlibrary.scraper import extract_ig_handle, extract_fb_handle


@dataclass
class BrandResult:
    """Resultado de extracción de marca."""
    brand_name: str              # Siempre string no vacío
    page_id: Optional[str]       # Page ID de Facebook
    confidence: float            # 0.0-1.0
    source: str                  # "fb_ig_validated" | "fb_only" | "ig_only" | "fallback"
    fb_display_name: Optional[str] = None
    ig_display_name: Optional[str] = None
    validation_passed: bool = False  # True si FB e IG coinciden
    errors: list = None          # Lista de errores para debugging
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BrandExtractor:
    """Extractor de brand name con validación cruzada FB/IG."""
    
    def __init__(self):
        self.api_key = settings.FIRECRAWL_API_KEY
        self.base_url = settings.FIRECRAWL_BASE_URL
        self.timeout = 30.0
    
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def extract_username(self, url: str, platform: str) -> Optional[str]:
        """
        Extrae username de una URL de red social.
        Delegates to centralized extract_ig_handle / extract_fb_handle.
        """
        if platform == "instagram":
            return extract_ig_handle(url)
        elif platform == "facebook":
            return extract_fb_handle(url)
        return None
    
    async def search_ad_library(
        self, 
        username: str,
        client: httpx.AsyncClient
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Busca un username en Ad Library y extrae page_id y display_name.
        
        Args:
            username: Username de FB/IG a buscar
            client: Cliente HTTP activo
            
        Returns:
            Tuple de (page_id, display_name) o (None, None) si no encuentra
        """
        try:
            print(f"       [BrandExtractor] Buscando '{username}' en Ad Library...")
            
            # Estrategia 1: Búsqueda directa en Ad Library
            search_queries = [
                f'"{username}" site:facebook.com/ads/library view_all_page_id',
                f'{username} site:facebook.com/ads/library',
            ]
            
            for query in search_queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/search",
                        headers=self._get_headers(),
                        json={"query": query, "limit": 5},
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        for result in data.get("data", []):
                            url = result.get("url", "")
                            
                            # Buscar page_id en URL
                            page_id_match = re.search(r'view_all_page_id=(\d+)', url)
                            if page_id_match:
                                page_id = page_id_match.group(1)
                                
                                # Intentar obtener display_name del resultado
                                title = result.get("title", "")
                                display_name = self._extract_display_name_from_title(title, username)
                                
                                print(f"       [BrandExtractor] [OK] Encontrado: page_id={page_id}, name='{display_name}'")
                                return page_id, display_name
                                
                except Exception as e:
                    print(f"       [BrandExtractor] Error en búsqueda: {str(e)[:50]}")
                    continue
            
            # Estrategia 2: Scrape directo de Ad Library con el username
            print(f"       [BrandExtractor] Intentando scrape directo de Ad Library...")
            ad_lib_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={username}&search_type=keyword_exact_phrase"
            
            try:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers=self._get_headers(),
                    json={
                        "url": ad_lib_url,
                        "formats": ["markdown"],
                        "waitFor": 5000
                    },
                    timeout=45.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    markdown = result.get("data", {}).get("markdown", "")
                    
                    # Buscar page_id en el contenido
                    page_id_match = re.search(r'view_all_page_id=(\d+)', markdown)
                    if page_id_match:
                        page_id = page_id_match.group(1)
                        
                        # Buscar display name en markdown
                        # Patrón: [Display Name](https://facebook.com/...) **Sponsored**
                        name_match = re.search(
                            r'\[([^\]]+)\]\(https://(?:www\.)?facebook\.com/[^)]+\)\s*\*\*Sponsored\*\*',
                            markdown
                        )
                        display_name = name_match.group(1) if name_match else username
                        
                        print(f"       [BrandExtractor] [OK] Encontrado via scrape: page_id={page_id}, name='{display_name}'")
                        return page_id, display_name
                        
            except Exception as e:
                print(f"       [BrandExtractor] Error en scrape: {str(e)[:50]}")
            
            print(f"       [BrandExtractor] [X] No se encontro '{username}' en Ad Library")
            return None, None
            
        except Exception as e:
            print(f"       [BrandExtractor] Error general: {e}")
            return None, None
    
    def _extract_display_name_from_title(self, title: str, fallback: str) -> str:
        """Extrae display name from search result title."""
        if not title:
            return fallback
        
        # Limpiar título
        # Ejemplo: "Nike | Ad Library | Facebook" -> "Nike"
        # Also handles: "Ad Library - Facebook", "Meta Ad Library", etc.
        
        # Split on both | and - separators
        parts = re.split(r'[|\-–—]', title)
        if parts:
            name = parts[0].strip()
            name_lower = name.lower()
            
            # Reject if the extracted name IS a generic/platform term
            GENERIC_NAMES = ['ad library', 'facebook', 'meta', 'ads', 'instagram',
                             'meta ad library', 'facebook ads', 'fb ads', 'biblioteca de anuncios']
            
            if name_lower in GENERIC_NAMES:
                return fallback
            
            # Reject if the name CONTAINS "ad library" (e.g. "Ad Library - Facebook")
            if 'ad library' in name_lower or 'biblioteca de anuncios' in name_lower:
                return fallback
            
            # Reject if it's too short (likely garbage)
            if len(name) < 2:
                return fallback
            
            return name
        
        return fallback
    
    async def validate_brand(
        self,
        fb_username: Optional[str],
        ig_username: Optional[str],
        fallback_name: str
    ) -> BrandResult:
        """
        Valida marca buscando FB e IG en Ad Library.
        
        Args:
            fb_username: Username de Facebook
            ig_username: Username de Instagram
            fallback_name: Nombre a usar si todo falla
            
        Returns:
            BrandResult con el mejor nombre encontrado
        """
        errors = []
        fb_page_id = None
        fb_display_name = None
        ig_page_id = None
        ig_display_name = None
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Buscar FB
            if fb_username:
                try:
                    fb_page_id, fb_display_name = await self.search_ad_library(fb_username, client)
                except Exception as e:
                    errors.append(f"FB search error: {str(e)[:100]}")
            
            # Buscar IG
            if ig_username:
                try:
                    ig_page_id, ig_display_name = await self.search_ad_library(ig_username, client)
                except Exception as e:
                    errors.append(f"IG search error: {str(e)[:100]}")
        
        # Validación cruzada
        if fb_page_id and ig_page_id:
            if fb_page_id == ig_page_id:
                # Validado - ambos apuntan a la misma página
                print(f"       [BrandExtractor] [VALIDATED] FB e IG coinciden (page_id={fb_page_id})")
                return BrandResult(
                    brand_name=fb_display_name or ig_display_name or fb_username,
                    page_id=fb_page_id,
                    confidence=1.0,
                    source="fb_ig_validated",
                    fb_display_name=fb_display_name,
                    ig_display_name=ig_display_name,
                    validation_passed=True,
                    errors=errors
                )
            else:
                # Diferentes page_ids - usar FB como primario
                print(f"       [BrandExtractor] [WARN] FB e IG tienen page_ids diferentes. Usando FB.")
                errors.append(f"Page ID mismatch: FB={fb_page_id}, IG={ig_page_id}")
                return BrandResult(
                    brand_name=fb_display_name or fb_username,
                    page_id=fb_page_id,
                    confidence=0.8,
                    source="fb_only",
                    fb_display_name=fb_display_name,
                    ig_display_name=ig_display_name,
                    validation_passed=False,
                    errors=errors
                )
        
        # Solo FB encontrado
        if fb_page_id:
            print(f"       [BrandExtractor] [OK] Solo FB encontrado")
            return BrandResult(
                brand_name=fb_display_name or fb_username,
                page_id=fb_page_id,
                confidence=0.7,
                source="fb_only",
                fb_display_name=fb_display_name,
                validation_passed=False,
                errors=errors
            )
        
        # Solo IG encontrado
        if ig_page_id:
            print(f"       [BrandExtractor] [OK] Solo IG encontrado")
            return BrandResult(
                brand_name=ig_display_name or ig_username,
                page_id=ig_page_id,
                confidence=0.7,
                source="ig_only",
                ig_display_name=ig_display_name,
                validation_passed=False,
                errors=errors
            )
        
        # Ninguno encontrado - fallback
        print(f"       [BrandExtractor] [X] Ninguno encontrado, usando fallback: '{fallback_name}'")
        errors.append("No Ad Library results for FB or IG username")
        return BrandResult(
            brand_name=fallback_name,
            page_id=None,
            confidence=0.5,
            source="fallback",
            validation_passed=False,
            errors=errors
        )
    
    async def get_brand_name(
        self,
        social_media_urls: dict,
        fallback_name: str
    ) -> BrandResult:
        """
        Entry point principal - obtiene brand name desde social media URLs.
        
        Args:
            social_media_urls: Dict con URLs {"facebook": "...", "instagram": "..."}
            fallback_name: Nombre a usar si no se encuentra nada
            
        Returns:
            BrandResult con el mejor nombre encontrado
        """
        print(f"    [BrandExtractor] Iniciando extracción para '{fallback_name}'...")
        
        # Extraer usernames
        fb_url = social_media_urls.get("facebook")
        ig_url = social_media_urls.get("instagram")
        
        fb_username = self.extract_username(fb_url, "facebook") if fb_url else None
        ig_username = self.extract_username(ig_url, "instagram") if ig_url else None
        
        print(f"    [BrandExtractor] FB username: {fb_username or 'N/A'}")
        print(f"    [BrandExtractor] IG username: {ig_username or 'N/A'}")
        
        if not fb_username and not ig_username:
            print(f"    [BrandExtractor] No hay usernames disponibles, usando fallback")
            return BrandResult(
                brand_name=fallback_name,
                page_id=None,
                confidence=0.3,
                source="no_social_urls",
                validation_passed=False,
                errors=["No Facebook or Instagram URLs available"]
            )
        
        # Validar y obtener brand name
        result = await self.validate_brand(fb_username, ig_username, fallback_name)
        
        print(f"    [BrandExtractor] Resultado: '{result.brand_name}' (confidence={result.confidence}, source={result.source})")
        
        return result


# Singleton para uso global
_brand_extractor = None

def get_brand_extractor() -> BrandExtractor:
    """Get or create BrandExtractor singleton."""
    global _brand_extractor
    if _brand_extractor is None:
        _brand_extractor = BrandExtractor()
    return _brand_extractor
