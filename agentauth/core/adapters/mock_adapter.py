import random
import time
from typing import Any

from . import adapter_registry
from .base import BaseAdapter


@adapter_registry.register("mock")
class MockAdapter(BaseAdapter):
    """Simulates a successful downstream API response. Good for testing proxy routing and IAM blocks."""

    requires_auth = False

    def __init__(self, **kwargs: Any) -> None:
        """Ignore any provided credentials or settings."""
        super().__init__(**kwargs)

    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        # Simulate network latency
        time.sleep(0.3)

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
