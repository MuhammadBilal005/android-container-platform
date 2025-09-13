import asyncio
import random
import time
from typing import Dict, List, Optional, Tuple
import aiohttp
import requests

class ProxyManager:
    """Manages proxy pools and selection"""
    
    def __init__(self):
        self.proxy_pools = {
            "residential": [],
            "datacenter": [],
            "mobile": [],
            "free": []
        }
        self.geo_proxies = {}  # country -> [proxies]
        self.working_proxies = set()
        self.proxy_stats = {}
    
    async def initialize(self):
        """Initialize proxy pools with default providers"""
        
        # Add some example proxy configurations
        # In production, these would be loaded from config or external APIs
        
        # Residential proxies (example - replace with real providers)
        residential_proxies = [
            {
                "type": "residential",
                "host": "residential.proxy1.com",
                "port": 8080,
                "username": "user1",
                "password": "pass1",
                "country": "US",
                "city": "New York",
                "provider": "ProxyProvider1"
            },
            {
                "type": "residential", 
                "host": "residential.proxy2.com",
                "port": 8080,
                "username": "user2", 
                "password": "pass2",
                "country": "UK",
                "city": "London",
                "provider": "ProxyProvider2"
            }
        ]
        
        # Datacenter proxies
        datacenter_proxies = [
            {
                "type": "datacenter",
                "host": "datacenter.proxy1.com",
                "port": 3128,
                "username": "dc_user1",
                "password": "dc_pass1",
                "country": "DE",
                "city": "Frankfurt",
                "provider": "DataCenter1"
            },
            {
                "type": "datacenter",
                "host": "datacenter.proxy2.com", 
                "port": 3128,
                "username": "dc_user2",
                "password": "dc_pass2",
                "country": "SG",
                "city": "Singapore",
                "provider": "DataCenter2"
            }
        ]
        
        # Mobile proxies
        mobile_proxies = [
            {
                "type": "mobile",
                "host": "mobile.proxy1.com",
                "port": 8000,
                "username": "mobile1",
                "password": "mobile_pass1",
                "country": "US",
                "city": "Los Angeles",
                "provider": "MobileProvider1",
                "carrier": "Verizon"
            }
        ]
        
        # Free proxies (for testing - not recommended for production)
        free_proxies = [
            {
                "type": "free",
                "host": "free-proxy1.com",
                "port": 8080,
                "country": "US",
                "provider": "FreeProxy"
            },
            {
                "type": "free",
                "host": "free-proxy2.com", 
                "port": 3128,
                "country": "CA",
                "provider": "FreeProxy2"
            }
        ]
        
        # Add to pools
        self.proxy_pools["residential"] = residential_proxies
        self.proxy_pools["datacenter"] = datacenter_proxies
        self.proxy_pools["mobile"] = mobile_proxies
        self.proxy_pools["free"] = free_proxies
        
        # Organize by geography
        all_proxies = []
        for proxy_list in self.proxy_pools.values():
            all_proxies.extend(proxy_list)
        
        for proxy in all_proxies:
            country = proxy.get("country", "Unknown")
            if country not in self.geo_proxies:
                self.geo_proxies[country] = []
            self.geo_proxies[country].append(proxy)
        
        # Test all proxies on startup
        await self.test_all_proxies()
    
    async def get_proxy(self, proxy_type: Optional[str] = None,
                       country: Optional[str] = None,
                       city: Optional[str] = None,
                       exclude_failed: bool = True) -> Optional[Dict]:
        """Get a suitable proxy based on criteria"""
        
        candidates = []
        
        # Filter by type
        if proxy_type:
            candidates = self.proxy_pools.get(proxy_type, [])
        else:
            # Get all proxies
            for proxy_list in self.proxy_pools.values():
                candidates.extend(proxy_list)
        
        # Filter by geography
        if country:
            candidates = [p for p in candidates if p.get("country") == country]
        
        if city:
            candidates = [p for p in candidates if p.get("city") == city]
        
        # Filter out failed proxies if requested
        if exclude_failed:
            candidates = [p for p in candidates 
                         if self._is_proxy_working(p)]
        
        if not candidates:
            return None
        
        # Select best proxy based on performance
        return self._select_best_proxy(candidates)
    
    def _is_proxy_working(self, proxy: Dict) -> bool:
        """Check if proxy is currently working"""
        proxy_key = f"{proxy['host']}:{proxy['port']}"
        return proxy_key in self.working_proxies
    
    def _select_best_proxy(self, candidates: List[Dict]) -> Dict:
        """Select best proxy from candidates based on performance"""
        
        if not candidates:
            return None
        
        # Score proxies based on various factors
        scored_proxies = []
        
        for proxy in candidates:
            score = 0
            proxy_key = f"{proxy['host']}:{proxy['port']}"
            stats = self.proxy_stats.get(proxy_key, {})
            
            # Response time score (lower is better)
            response_time = stats.get("avg_response_time", 1000)
            score += max(0, 100 - (response_time / 10))
            
            # Success rate score
            success_rate = stats.get("success_rate", 0.5)
            score += success_rate * 100
            
            # Proxy type preference (residential > mobile > datacenter > free)
            type_scores = {
                "residential": 50,
                "mobile": 40,
                "datacenter": 30,
                "free": 10
            }
            score += type_scores.get(proxy.get("type"), 0)
            
            # Recent usage penalty (avoid overusing same proxy)
            last_used = stats.get("last_used", 0)
            time_since_use = time.time() - last_used
            if time_since_use < 300:  # 5 minutes
                score -= 20
            
            scored_proxies.append((proxy, score))
        
        # Sort by score and return best
        scored_proxies.sort(key=lambda x: x[1], reverse=True)
        
        # Add some randomness to top choices to distribute load
        top_proxies = scored_proxies[:3]
        return random.choice(top_proxies)[0]
    
    async def test_proxy(self, proxy: Dict, timeout: int = 10) -> Tuple[bool, Optional[int]]:
        """Test a single proxy and return (is_working, response_time_ms)"""
        
        try:
            proxy_url = self._build_proxy_url(proxy)
            
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://httpbin.org/ip',
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    end_time = time.time()
                    response_time = int((end_time - start_time) * 1000)
                    
                    if response.status == 200:
                        data = await response.json()
                        # Verify we got a different IP
                        if 'origin' in data:
                            self._update_proxy_stats(proxy, True, response_time)
                            return True, response_time
            
            self._update_proxy_stats(proxy, False, None)
            return False, None
            
        except Exception as e:
            self._update_proxy_stats(proxy, False, None)
            return False, None
    
    def _build_proxy_url(self, proxy: Dict) -> str:
        """Build proxy URL from proxy configuration"""
        
        auth = ""
        if proxy.get("username") and proxy.get("password"):
            auth = f"{proxy['username']}:{proxy['password']}@"
        
        return f"http://{auth}{proxy['host']}:{proxy['port']}"
    
    def _update_proxy_stats(self, proxy: Dict, success: bool, response_time: Optional[int]):
        """Update proxy performance statistics"""
        
        proxy_key = f"{proxy['host']}:{proxy['port']}"
        
        if proxy_key not in self.proxy_stats:
            self.proxy_stats[proxy_key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "response_times": [],
                "avg_response_time": 0,
                "success_rate": 0,
                "last_used": 0,
                "last_test": time.time()
            }
        
        stats = self.proxy_stats[proxy_key]
        stats["total_requests"] += 1
        stats["last_test"] = time.time()
        
        if success:
            stats["successful_requests"] += 1
            if response_time:
                stats["response_times"].append(response_time)
                # Keep only last 50 response times
                if len(stats["response_times"]) > 50:
                    stats["response_times"] = stats["response_times"][-50:]
                stats["avg_response_time"] = sum(stats["response_times"]) / len(stats["response_times"])
            
            # Add to working proxies
            self.working_proxies.add(proxy_key)
        else:
            stats["failed_requests"] += 1
            # Remove from working proxies
            self.working_proxies.discard(proxy_key)
        
        # Update success rate
        stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
    
    async def test_all_proxies(self):
        """Test all proxies in pools"""
        
        print("Testing all proxies...")
        
        all_proxies = []
        for proxy_list in self.proxy_pools.values():
            all_proxies.extend(proxy_list)
        
        # Test proxies concurrently in batches
        batch_size = 10
        for i in range(0, len(all_proxies), batch_size):
            batch = all_proxies[i:i + batch_size]
            tasks = [self.test_proxy(proxy) for proxy in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(results):
                if not isinstance(result, Exception):
                    is_working, response_time = result
                    proxy = batch[j]
                    status = "✓" if is_working else "✗"
                    print(f"{status} {proxy['host']}:{proxy['port']} - {response_time}ms" if response_time else f"{status} {proxy['host']}:{proxy['port']}")
            
            # Small delay between batches to avoid overwhelming proxies
            await asyncio.sleep(1)
        
        working_count = len(self.working_proxies)
        total_count = len(all_proxies)
        print(f"Proxy testing complete: {working_count}/{total_count} working")
    
    async def get_random_proxy(self, proxy_type: Optional[str] = None) -> Optional[Dict]:
        """Get a random working proxy"""
        
        candidates = []
        
        if proxy_type:
            candidates = [p for p in self.proxy_pools.get(proxy_type, [])
                         if self._is_proxy_working(p)]
        else:
            for proxy_list in self.proxy_pools.values():
                candidates.extend([p for p in proxy_list if self._is_proxy_working(p)])
        
        return random.choice(candidates) if candidates else None
    
    async def rotate_proxy(self, current_proxy: Optional[Dict], **criteria) -> Optional[Dict]:
        """Get a different proxy than the current one"""
        
        new_proxy = await self.get_proxy(**criteria)
        
        # Ensure we get a different proxy
        if current_proxy and new_proxy:
            current_key = f"{current_proxy['host']}:{current_proxy['port']}"
            new_key = f"{new_proxy['host']}:{new_proxy['port']}"
            
            if current_key == new_key:
                # Try to get another one
                candidates = []
                proxy_type = criteria.get("proxy_type")
                
                if proxy_type:
                    candidates = self.proxy_pools.get(proxy_type, [])
                else:
                    for proxy_list in self.proxy_pools.values():
                        candidates.extend(proxy_list)
                
                # Filter out current proxy and get another
                candidates = [p for p in candidates 
                             if f"{p['host']}:{p['port']}" != current_key
                             and self._is_proxy_working(p)]
                
                if candidates:
                    new_proxy = self._select_best_proxy(candidates)
        
        return new_proxy
    
    def get_proxy_stats(self) -> Dict:
        """Get overall proxy statistics"""
        
        total_proxies = sum(len(pool) for pool in self.proxy_pools.values())
        working_proxies = len(self.working_proxies)
        
        by_type = {}
        for proxy_type, proxies in self.proxy_pools.items():
            working = sum(1 for p in proxies if self._is_proxy_working(p))
            by_type[proxy_type] = {
                "total": len(proxies),
                "working": working,
                "success_rate": working / len(proxies) if proxies else 0
            }
        
        by_country = {}
        for country, proxies in self.geo_proxies.items():
            working = sum(1 for p in proxies if self._is_proxy_working(p))
            by_country[country] = {
                "total": len(proxies),
                "working": working,
                "success_rate": working / len(proxies) if proxies else 0
            }
        
        return {
            "total_proxies": total_proxies,
            "working_proxies": working_proxies,
            "overall_success_rate": working_proxies / total_proxies if total_proxies else 0,
            "by_type": by_type,
            "by_country": by_country
        }
    
    async def health_check_proxies(self):
        """Periodic health check of all proxies"""
        
        while True:
            try:
                await self.test_all_proxies()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                print(f"Proxy health check error: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute on error