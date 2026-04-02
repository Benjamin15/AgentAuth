from abc import ABC, abstractmethod
import time
from typing import Any, Dict

class BaseAdapter(ABC):
    """
    Base strategy for forwarding requests to upstream LLM or SaaS providers.
    """
    
    @abstractmethod
    async def forward(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw request data, formats it if needed, and sends it to the upstream API.
        """
        pass

class MockAdapter(BaseAdapter):
    """
    Simulates a successful downstream API response. Good for testing proxy routing and IAM blocks.
    """
    
    async def forward(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate network latency
        time.sleep(0.3)
        return {
            "status": "success",
            "message": "This is a simulated response from the downstream service.",
            "echoed_data": request_data
        }

class GeminiAdapter(BaseAdapter):
    """
    Real-world pass-through for Google Gemini API.
    """
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent?key={self.api_key}"


    async def forward(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.url, headers=headers, json=request_data)
        
        if response.status_code != 200:
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text
            }
            
        return response.json()

