from agentauth.dashboard.utils import get_icon, get_time_delta


def test_get_time_delta_logic():
    # 1h, 6h, 24h, 7d
    assert get_time_delta("1h") is not None
    assert get_time_delta("6h") is not None
    assert get_time_delta("24h") is not None
    assert get_time_delta("7d") is not None

    # Invalid
    assert get_time_delta("unknown") is None
    assert get_time_delta("") is None


def test_get_icon():
    icon_div = get_icon("openai")
    # The icon class is on the <i> component which is the first child
    icon_i = icon_div.children[0]
    assert "bi-cpu-fill" in icon_i.className


def test_get_icon_fallback():
    icon_div = get_icon("")
    icon_i = icon_div.children[0]
    assert "gear-fill" in icon_i.className


def test_icon_supported_providers():
    for provider in ["openai", "anthropic", "gemini", "cohere", "mistral", "pinecone"]:
        icon_div = get_icon(provider)
        assert icon_div.children[0].className != "bi bi-gear-fill"
