import datetime
from typing import Optional


def get_time_delta(time_range: str) -> Optional[datetime.datetime]:
    """Return a naive datetime for the start of the given range."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if time_range == "1h":
        return now - datetime.timedelta(hours=1)
    if time_range == "6h":
        return now - datetime.timedelta(hours=6)
    if time_range == "24h":
        return now - datetime.timedelta(days=1)
    if time_range == "7d":
        return now - datetime.timedelta(days=7)
    return None


SUPPORTED_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "desc": "GPT-4 & GPT-3.5",
        "type": "llm",
        "version": "v4.0.1",
        "region": "us-east-1",
    },
    "anthropic": {
        "name": "Anthropic",
        "desc": "Claude 3 Opus & Sonnet",
        "type": "llm",
        "version": "v3.0.0",
        "region": "us-west-2",
    },
    "gemini": {
        "name": "Google Gemini",
        "desc": "Gemini 1.5 Pro",
        "type": "llm",
        "version": "v1.5.0",
        "region": "global",
    },
    "cohere": {
        "name": "Cohere",
        "desc": "Command R+",
        "type": "llm",
        "version": "v2.1.0",
        "region": "us-central-1",
    },
    "mistral": {
        "name": "Mistral AI",
        "desc": "Mistral Large",
        "type": "llm",
        "version": "v1.0.0",
        "region": "eu-west-1",
    },
    "pinecone": {
        "name": "Pinecone",
        "desc": "Serverless vector DB",
        "type": "vector",
        "version": "v2.1.0 (Active)",
        "region": "us-east-1 (AWS)",
    },
}

# SVG paths for icons (Keep if needed in future, but get_icon uses Bootstrap Icons now)
PROVIDER_ICONS = {
    "openai": "M15.35 11c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41zm-6.67 0c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41zm6.67 4.44c0 1.25-1.02 2.22-2.22 2.22s-2.22-1.02-2.22-2.22v-.41c0-1.25 1.02-2.22 2.22-2.22s2.22 1.02 2.22 2.22v.41z",
    "anthropic": "M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z",
    "gemini": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z",
    "cohere": "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
    "mistral": "M12.89 3L5 21h3.39l1.61-4.67h4l1.61 4.67H19l-7.89-18h-1.22zM11 13l1-3 1 3h-2z",
    "pinecone": "M12 3L2 12h3v9h6v-6h2v6h6v-9h3L12 3z",
}


def get_icon(name: str, size: int = 24):
    from dash import html

    icon_map = {
        "openai": "bi bi-cpu-fill",
        "anthropic": "bi bi-robot",
        "gemini": "bi bi-stars",
        "cohere": "bi bi-box",
        "mistral": "bi bi-wind",
        "pinecone": "bi bi-database-fill",
    }
    icon_class = icon_map.get(name.lower(), "bi bi-gear-fill")
    return html.Div(
        style={
            "width": f"{size}px",
            "height": f"{size}px",
            "backgroundColor": "var(--bg-primary)",
            "borderRadius": "8px",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "marginRight": "12px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
            "flexShrink": "0",
        },
        children=[
            html.I(
                className=icon_class,
                style={"fontSize": f"{int(size * 0.5)}px", "color": "var(--primary-color)"},
            )
        ],
    )
