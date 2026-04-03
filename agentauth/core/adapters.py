import time
from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Base strategy for forwarding requests to upstream LLM or SaaS providers."""

    @abstractmethod
    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Take raw request data, format it if needed, and send it to the upstream API."""
        pass


class MockAdapter(BaseAdapter):
    """Simulates a successful downstream API response. Good for testing proxy routing and IAM blocks."""

    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        # Simulate network latency
        time.sleep(0.3)
        import random

        return {
            "status": "success",
            "model_name": "mock",
            "message": "This is a simulated response from the downstream service.",
            "echoed_data": request_data,
            "usage": {
                "prompt": random.randint(10, 100),
                "completion": random.randint(5, 50),
                "total": 0,  # calculated later if needed
            },
        }


class GeminiAdapter(BaseAdapter):
    """Real-world pass-through for Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent?key={self.api_key}"

    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        import requests

        headers = {"Content-Type": "application/json"}
        response = requests.post(self.url, headers=headers, json=request_data)

        if response.status_code != 200:
            return {"status": "error", "code": response.status_code, "message": response.text}

        data = response.json()
        usage = data.get("usageMetadata", {})

        return {
            "data": data,
            "model_name": self.model,
            "usage": {
                "prompt": usage.get("promptTokenCount"),
                "completion": usage.get("candidatesTokenCount"),
                "total": usage.get("totalTokenCount"),
            },
        }
