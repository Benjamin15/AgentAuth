import argparse
import sys

from .main import start


def main():
    """Command-line interface for AgentAuth."""
    parser = argparse.ArgumentParser(description="AgentAuth: IAM and Proxy for AI Agents.")
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host to bind the server to (default from settings).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind the server to (default from settings).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=None,
        help="Enable auto-reload on code changes (default from settings).",
    )

    parser.parse_args()

    try:
        start()
    except KeyboardInterrupt:
        print("\nStopping AgentAuth...")
        sys.exit(0)


if __name__ == "__main__":
    main()
