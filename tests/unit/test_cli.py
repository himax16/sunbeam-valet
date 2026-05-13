from pathlib import Path
from unittest.mock import MagicMock, patch

from sunbeam_valet import cli


async def _noop():
    return None


def test_main_runs_harness_with_config_path():
    with (
        patch("sunbeam_valet.cli.load_config") as mock_load_config,
        patch("sunbeam_valet.cli.Harness") as mock_harness_class,
        patch("sunbeam_valet.cli.asyncio.run") as mock_asyncio_run,
    ):
        coroutine = _noop()
        mock_harness = mock_harness_class.return_value
        mock_harness.run = MagicMock(return_value=coroutine)

        result = cli.main(["--config", "custom.yaml", "--log-level", "DEBUG"])
        coroutine.close()

    assert result == 0
    mock_load_config.assert_called_once_with(Path("custom.yaml"))
    mock_harness_class.assert_called_once_with(mock_load_config.return_value)
    mock_harness.run.assert_called_once_with()
    mock_asyncio_run.assert_called_once_with(coroutine)


def test_main_returns_error_for_invalid_config():
    with patch("sunbeam_valet.cli.load_config", side_effect=ValueError("missing value")):
        result = cli.main(["--config", "broken.yaml"])

    assert result == 1
