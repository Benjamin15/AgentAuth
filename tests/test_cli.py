import sys
from unittest.mock import patch

import pytest

from agentauth.cli import main


def test_cli_help():
    with patch.object(sys, "argv", ["agentauth", "--help"]):
        with patch("argparse.ArgumentParser.print_help"):
            # ArgumentParser.parse_args() will exit on --help
            with pytest.raises(SystemExit):
                main()


@patch("agentauth.cli.start")
def test_cli_execution(mock_start):
    with patch.object(sys, "argv", ["agentauth"]):
        main()
        mock_start.assert_called_once()


@patch("agentauth.cli.start", side_effect=KeyboardInterrupt)
def test_cli_interrupt(mock_start):
    with patch.object(sys, "argv", ["agentauth"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
