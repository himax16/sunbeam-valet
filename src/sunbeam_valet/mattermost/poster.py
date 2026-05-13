import httpx

from sunbeam_valet.config import MattermostConfig


class MattermostPoster:
    def __init__(self, config: MattermostConfig):
        self.config = config

    async def post(self, message: str) -> None:
        if self.config.mode == "webhook":
            await self._post_webhook(message)
            return
        await self._post_bot(message)

    async def _post_bot(self, message: str) -> None:
        assert self.config.server_url is not None
        assert self.config.bot_token is not None
        assert self.config.channel_id is not None

        payload = {
            "channel_id": self.config.channel_id,
            "message": message,
        }

        headers = {
            "Authorization": f"Bearer {self.config.bot_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.server_url.rstrip('/')}/api/v4/posts",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()

    async def _post_webhook(self, message: str) -> None:
        assert self.config.webhook_url is not None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.webhook_url,
                json={"text": message},
            )
            response.raise_for_status()
