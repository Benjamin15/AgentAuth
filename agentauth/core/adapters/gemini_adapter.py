from typing import Any

import requests

from . import adapter_registry
from .base import BaseAdapter


@adapter_registry.register("gemini")
class GeminiAdapter(BaseAdapter):
    """Real-world pass-through for Google Gemini API."""

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash", **kwargs: Any):
        """Initialize the Gemini adapter with provider-specific configuration."""
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent?key={self.api_key}"

    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
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
