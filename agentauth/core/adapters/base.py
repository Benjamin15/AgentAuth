from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Base strategy for forwarding requests to upstream LLM or SaaS providers."""

    # Whether this adapter requires a provider API key to function.
    requires_auth: bool = True

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the adapter with optional settings."""
        self._kwargs = kwargs

    @abstractmethod
    async def forward(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Take raw request data, format it if needed, and send it to the upstream API.

        Args:
        ----
            request_data: Raw JSON body from the incoming proxy request.

        Returns:
        -------
            A dictionary containing the response data and usage metrics.

        """
        pass
