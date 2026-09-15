"""GeoIP caching utility for IP to coordinate lookups."""
import asyncio
import json
import time
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache

import aiofiles
import aiohttp

from backend.config import settings
from backend.utils.redis_client import redis_manager

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Geographic location data for an IP address."""
    ip: str
    latitude: float
    longitude: float
    country: str
    city: str
    isp: str
    timestamp: float


class GeoIPCache:
    """Caches GeoIP lookups to avoid API rate limits."""
    
    def __init__(self):
        self._memory_cache: dict[str, GeoLocation] = {}
        self._cache_file = "geoip_cache.json"
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        try:
            import os
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    data = json.load(f)
                    for ip, loc_data in data.items():
                        self._memory_cache[ip] = GeoLocation(**loc_data)
                logger.info(f"Loaded {len(self._memory_cache)} GeoIP entries from cache")
        except Exception as e:
            logger.warning(f"Failed to load GeoIP cache: {e}")
    
    async def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            data = {ip: loc.__dict__ for ip, loc in self._memory_cache.items()}
            async with aiofiles.open(self._cache_file, 'w') as f:
                await f.write(json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Failed to save GeoIP cache: {e}")
    
    def _is_valid(self, location: GeoLocation) -> bool:
        """Check if cached location is still valid."""
        return (time.time() - location.timestamp) < settings.geoip_cache_ttl
    
    async def get_location(self, ip: str) -> Optional[GeoLocation]:
        """Get geographic location for an IP address."""
        # Skip private IPs
        if self._is_private_ip(ip):
            return GeoLocation(
                ip=ip,
                latitude=0.0,
                longitude=0.0,
                country="Private",
                city="Local",
                isp="Internal",
                timestamp=time.time()
            )
        
        # Check memory cache
        if ip in self._memory_cache and self._is_valid(self._memory_cache[ip]):
            return self._memory_cache[ip]
        
        # Check Redis cache
        cached = await redis_manager.get(f"geoip:{ip}")
        if cached:
            location = GeoLocation(**cached)
            if self._is_valid(location):
                self._memory_cache[ip] = location
                return location
        
        # Fetch from API
        location = await self._fetch_from_api(ip)
        if location:
            self._memory_cache[ip] = location
            await redis_manager.set(f"geoip:{ip}", location.__dict__, expire=settings.geoip_cache_ttl)
            await self._save_cache()
        
        return location
    
    async def _fetch_from_api(self, ip: str) -> Optional[GeoLocation]:
        """Fetch location from external API."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{settings.geoip_api_url}{ip}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success":
                            return GeoLocation(
                                ip=ip,
                                latitude=data.get("lat", 0.0),
                                longitude=data.get("lon", 0.0),
                                country=data.get("country", "Unknown"),
                                city=data.get("city", "Unknown"),
                                isp=data.get("isp", "Unknown"),
                                timestamp=time.time()
                            )
        except Exception as e:
            logger.warning(f"GeoIP lookup failed for {ip}: {e}")
        
        # Return default location on failure
        return GeoLocation(
            ip=ip,
            latitude=0.0,
            longitude=0.0,
            country="Unknown",
            city="Unknown",
            isp="Unknown",
            timestamp=time.time()
        )
    
    @staticmethod
    def _is_private_ip(ip: str) -> bool:
        """Check if IP is private/internal."""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        first = int(parts[0])
        second = int(parts[1])
        
        # RFC 1918 private ranges
        if first == 10:
            return True
        if first == 172 and 16 <= second <= 31:
            return True
        if first == 192 and second == 168:
            return True
        # Loopback
        if first == 127:
            return True
        # Link-local
        if first == 169 and second == 254:
            return True
        
        return False
    
    async def get_batch_locations(self, ips: list[str]) -> dict[str, GeoLocation]:
        """Get locations for multiple IPs efficiently."""
        results = {}
        uncached = []
        
        for ip in ips:
            if ip in self._memory_cache and self._is_valid(self._memory_cache[ip]):
                results[ip] = self._memory_cache[ip]
            else:
                uncached.append(ip)
        
        # Fetch uncached in parallel (with rate limiting)
        semaphore = asyncio.Semaphore(10)
        
        async def fetch_one(ip: str):
            async with semaphore:
                return await self.get_location(ip)
        
        if uncached:
            tasks = [fetch_one(ip) for ip in uncached]
            locations = await asyncio.gather(*tasks)
            for ip, loc in zip(uncached, locations):
                if loc:
                    results[ip] = loc
        
        return results


# Global cache instance
geoip_cache = GeoIPCache()


async def get_location(ip: str) -> Optional[GeoLocation]:
    """Convenience function to get location for an IP."""
    return await geoip_cache.get_location(ip)


async def get_batch_locations(ips: list[str]) -> dict[str, GeoLocation]:
    """Convenience function to get locations for multiple IPs."""
    return await geoip_cache.get_batch_locations(ips)