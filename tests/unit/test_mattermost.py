from unittest.mock import MagicMock, patch

import pytest

from sunbeam_valet.config import MattermostConfig
from sunbeam_valet.mattermost.poster import MattermostPoster


@pytest.mark.asyncio
async def test_post_uses_mattermost_bot_api():
    config = MattermostConfig(
        server_url="https://mattermost.example.com/",
        bot_token="test-token",
        channel_id="channel-id",
    )

    with patch("sunbeam_valet.mattermost.poster.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response

        await MattermostPoster(config).post("hello")

    mock_client.post.assert_awaited_once_with(
        "https://mattermost.example.com/api/v4/posts",
        json={"channel_id": "channel-id", "message": "hello"},
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        },
    )
    assert mock_client.post.await_count == 1


@pytest.mark.asyncio
async def test_post_uses_mattermost_webhook():
    config = MattermostConfig(
        mode="webhook",
        webhook_url="https://mattermost.example.com/hooks/test-hook",
    )

    with patch("sunbeam_valet.mattermost.poster.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response

        await MattermostPoster(config).post("hello")

    mock_client.post.assert_awaited_once_with(
        "https://mattermost.example.com/hooks/test-hook",
        json={"text": "hello"},
    )
