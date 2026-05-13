import json
from unittest.mock import AsyncMock, patch

import pytest

from sunbeam_valet.config import WatchtowerBugFilter, WatchtowerConfig
from sunbeam_valet.fetchers.watchtower import WatchtowerFetcher


class FakeProcess:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes = b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_fetch_uses_exec_and_filters_statuses():
    raw = [
        {
            "id": "1",
            "title": "Keep",
            "status": "New",
            "importance": "Medium",
            "description": "desc",
            "url": "https://bugs.launchpad.net/bugs/1",
        },
        {
            "id": "2",
            "title": "Drop",
            "status": "Fix Released",
            "importance": "Low",
            "description": "desc",
            "url": "https://bugs.launchpad.net/bugs/2",
        },
    ]
    config = WatchtowerConfig(
        command=["watchtower", "bugs", "--format", "json"],
        bug_filter=WatchtowerBugFilter(status=["New"]),
    )

    with patch(
        "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=FakeProcess(0, json.dumps(raw).encode())),
    ) as mock_exec:
        bugs = await WatchtowerFetcher(config).fetch()

    mock_exec.assert_called_once()
    assert mock_exec.call_args.args[:3] == ("watchtower", "bugs", "--format")
    assert [bug.id for bug in bugs] == ["1"]


@pytest.mark.asyncio
async def test_fetch_raises_for_failed_command():
    config = WatchtowerConfig(command=["watchtower"])

    with (
        patch(
            "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=FakeProcess(1, b"", b"boom")),
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await WatchtowerFetcher(config).fetch()


@pytest.mark.asyncio
async def test_fetch_raises_for_non_list_json():
    config = WatchtowerConfig(command=["watchtower"])

    with (
        patch(
            "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=FakeProcess(0, b'{"id": "1"}')),
        ),
        pytest.raises(ValueError, match="JSON list"),
    ):
        await WatchtowerFetcher(config).fetch()


@pytest.mark.asyncio
async def test_fetch_wraps_invalid_json_with_context():
    config = WatchtowerConfig(command=["watchtower"])

    with (
        patch(
            "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=FakeProcess(0, b"not-json")),
        ),
        pytest.raises(ValueError, match="invalid JSON"),
    ):
        await WatchtowerFetcher(config).fetch()


@pytest.mark.asyncio
async def test_fetch_wraps_invalid_item_with_index():
    config = WatchtowerConfig(command=["watchtower"])

    with (
        patch(
            "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=FakeProcess(0, b'["not-a-bug"]')),
        ),
        pytest.raises(ValueError, match="index 0"),
    ):
        await WatchtowerFetcher(config).fetch()


@pytest.mark.asyncio
async def test_fetch_rejects_missing_required_bug_fields():
    config = WatchtowerConfig(command=["watchtower"])

    with (
        patch(
            "sunbeam_valet.fetchers.watchtower.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=FakeProcess(0, b'[{"id": "1"}]')),
        ),
        pytest.raises(ValueError, match="index 0"),
    ):
        await WatchtowerFetcher(config).fetch()
