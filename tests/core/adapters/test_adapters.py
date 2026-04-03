from unittest.mock import MagicMock, patch

import pytest

from agentauth.core.adapters.base import BaseAdapter
from agentauth.core.adapters.gemini_adapter import GeminiAdapter
from agentauth.core.adapters.mock_adapter import MockAdapter


@pytest.mark.asyncio
async def test_base_adapter_coverage():
    class TestAdapter(BaseAdapter):
        async def forward(self, payload: dict) -> dict:
            return await super().forward(payload)  # type: ignore[safe-super]

    adapter = TestAdapter()
    res = await adapter.forward({})
    assert res is None


@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = MockAdapter()
    response = await adapter.forward({"test": "data"})
    assert response["status"] == "success"
    assert response["echoed_data"] == {"test": "data"}


@pytest.mark.asyncio
@patch("requests.post")
async def test_gemini_adapter_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}
    mock_post.return_value = mock_response

    adapter = GeminiAdapter(api_key="test_key")
    response = await adapter.forward({"contents": []})

    assert "data" in response
    assert response["data"]["candidates"][0]["content"]["parts"][0]["text"] == "Hello"


@pytest.mark.asyncio
@patch("requests.post")
async def test_gemini_adapter_error(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    adapter = GeminiAdapter(api_key="test_key")
    response = await adapter.forward({"contents": []})

    assert response["status"] == "error"
    assert response["code"] == 400
    assert response["message"] == "Bad Request"
