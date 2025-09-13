import asyncio
from typing import Dict, List, Optional
import httpx
import aiohttp

class ServiceClient:
    """HTTP client for communicating with backend services"""
    
    def __init__(self):
        self.identity_url = None
        self.location_url = None
        self.network_url = None
        self.lifecycle_url = None
        self.timeout = httpx.Timeout(30.0)
    
    async def initialize(self, identity_url: str, location_url: str, 
                        network_url: str, lifecycle_url: str):
        """Initialize service URLs"""
        self.identity_url = identity_url
        self.location_url = location_url
        self.network_url = network_url
        self.lifecycle_url = lifecycle_url
    
    async def _make_request(self, method: str, url: str, **kwargs):
        """Make HTTP request with error handling"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise Exception("Resource not found")
            elif e.response.status_code == 400:
                try:
                    error_detail = e.response.json().get("detail", "Bad request")
                except:
                    error_detail = "Bad request"
                raise Exception(f"Bad request: {error_detail}")
            else:
                raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
                
        except httpx.TimeoutException:
            raise Exception("Request timeout")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    # Identity service methods
    async def generate_identity(self, config: Dict):
        """Generate device identity"""
        return await self._make_request(
            "POST", 
            f"{self.identity_url}/generate-identity",
            json=config
        )
    
    async def get_identity(self, instance_id: str):
        """Get device identity"""
        return await self._make_request(
            "GET",
            f"{self.identity_url}/identity/{instance_id}"
        )
    
    # Lifecycle service methods
    async def create_instance(self, config: Dict):
        """Create Android instance"""
        return await self._make_request(
            "POST",
            f"{self.lifecycle_url}/instance/create",
            json=config
        )
    
    async def get_instance(self, instance_id: str):
        """Get instance details"""
        return await self._make_request(
            "GET",
            f"{self.lifecycle_url}/instance/{instance_id}"
        )
    
    async def list_instances(self, status: Optional[str] = None, limit: int = 100):
        """List instances"""
        params = {"limit": limit}
        if status:
            params["status"] = status
            
        return await self._make_request(
            "GET",
            f"{self.lifecycle_url}/instances",
            params=params
        )
    
    async def start_instance(self, instance_id: str):
        """Start instance"""
        return await self._make_request(
            "POST",
            f"{self.lifecycle_url}/instance/{instance_id}/start"
        )
    
    async def stop_instance(self, instance_id: str):
        """Stop instance"""
        return await self._make_request(
            "POST",
            f"{self.lifecycle_url}/instance/{instance_id}/stop"
        )
    
    async def restart_instance(self, instance_id: str):
        """Restart instance"""
        return await self._make_request(
            "POST",
            f"{self.lifecycle_url}/instance/{instance_id}/restart"
        )
    
    async def delete_instance(self, instance_id: str):
        """Delete instance"""
        return await self._make_request(
            "DELETE",
            f"{self.lifecycle_url}/instance/{instance_id}"
        )
    
    async def get_instance_logs(self, instance_id: str, lines: int = 100):
        """Get instance logs"""
        return await self._make_request(
            "GET",
            f"{self.lifecycle_url}/instance/{instance_id}/logs",
            params={"lines": lines}
        )
    
    async def get_instance_stats(self, instance_id: str):
        """Get instance statistics"""
        return await self._make_request(
            "GET",
            f"{self.lifecycle_url}/instance/{instance_id}/stats"
        )
    
    async def get_platform_stats(self):
        """Get platform statistics"""
        return await self._make_request(
            "GET",
            f"{self.lifecycle_url}/stats"
        )
    
    async def execute_command(self, instance_id: str, command: str):
        """Execute command in instance"""
        return await self._make_request(
            "POST",
            f"{self.lifecycle_url}/instance/{instance_id}/exec",
            json={"command": command}
        )
    
    # Location service methods
    async def set_location(self, instance_id: str, location: Dict):
        """Set instance location"""
        return await self._make_request(
            "POST",
            f"{self.location_url}/location/{instance_id}",
            json=location
        )
    
    async def get_location(self, instance_id: str):
        """Get current location"""
        return await self._make_request(
            "GET",
            f"{self.location_url}/location/{instance_id}"
        )
    
    async def start_route_simulation(self, instance_id: str, route_config: Dict):
        """Start route simulation"""
        return await self._make_request(
            "POST",
            f"{self.location_url}/route/{instance_id}",
            json=route_config
        )
    
    async def stop_route_simulation(self, instance_id: str):
        """Stop route simulation"""
        return await self._make_request(
            "POST",
            f"{self.location_url}/route/{instance_id}/stop"
        )
    
    async def get_location_history(self, instance_id: str, limit: int = 100):
        """Get location history"""
        return await self._make_request(
            "GET",
            f"{self.location_url}/location/{instance_id}/history",
            params={"limit": limit}
        )
    
    async def set_random_location(self, instance_id: str, center_lat: float = 40.7128,
                                center_lng: float = -74.0060, radius_km: float = 10.0):
        """Set random location"""
        return await self._make_request(
            "POST",
            f"{self.location_url}/location/{instance_id}/random",
            params={
                "center_lat": center_lat,
                "center_lng": center_lng, 
                "radius_km": radius_km
            }
        )
    
    async def set_city_location(self, instance_id: str, city: str, country: str = "US"):
        """Set city location"""
        return await self._make_request(
            "POST",
            f"{self.location_url}/location/{instance_id}/city",
            params={"city": city, "country": country}
        )
    
    # Network service methods
    async def configure_network(self, instance_id: str, config: Dict):
        """Configure network"""
        return await self._make_request(
            "POST",
            f"{self.network_url}/network/{instance_id}",
            json=config
        )
    
    async def get_network_config(self, instance_id: str):
        """Get network configuration"""
        return await self._make_request(
            "GET",
            f"{self.network_url}/network/{instance_id}"
        )
    
    async def update_proxy(self, instance_id: str, proxy_config: Dict):
        """Update proxy configuration"""
        return await self._make_request(
            "PUT",
            f"{self.network_url}/network/{instance_id}/proxy",
            json=proxy_config
        )
    
    async def get_network_status(self, instance_id: str):
        """Get network status"""
        return await self._make_request(
            "GET",
            f"{self.network_url}/network/{instance_id}/status"
        )
    
    async def test_network(self, instance_id: str):
        """Test network connectivity"""
        return await self._make_request(
            "POST",
            f"{self.network_url}/network/{instance_id}/test"
        )
    
    async def list_proxies(self, proxy_type: Optional[str] = None,
                          country: Optional[str] = None):
        """List available proxies"""
        params = {}
        if proxy_type:
            params["proxy_type"] = proxy_type
        if country:
            params["country"] = country
            
        return await self._make_request(
            "GET",
            f"{self.network_url}/proxy/list",
            params=params
        )
    
    async def add_proxy(self, proxy_config: Dict):
        """Add new proxy"""
        return await self._make_request(
            "POST",
            f"{self.network_url}/proxy/add",
            json=proxy_config
        )
    
    # Health check methods
    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        
        service_urls = {
            "identity": f"{self.identity_url}/health" if self.identity_url else None,
            "location": f"{self.location_url}/health" if self.location_url else None,
            "network": f"{self.network_url}/health" if self.network_url else None,
            "lifecycle": f"{self.lifecycle_url}/health" if self.lifecycle_url else None
        }
        
        url = service_urls.get(service_name)
        if not url:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url)
                return response.status_code == 200
        except:
            return False
    
    async def check_all_services_health(self) -> Dict[str, bool]:
        """Check health of all services"""
        
        services = ["identity", "location", "network", "lifecycle"]
        
        # Check all services concurrently
        tasks = [self.check_service_health(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_status = {}
        for service, result in zip(services, results):
            if isinstance(result, Exception):
                health_status[service] = False
            else:
                health_status[service] = result
        
        return health_status