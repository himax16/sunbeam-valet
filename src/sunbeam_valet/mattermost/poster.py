import httpx

from sunbeam_valet.config import MattermostConfig


class MattermostPoster:
    def __init__(self, config: MattermostConfig):
        self.server_url = config.server_url.rstrip("/")
        self.bot_token = config.bot_token
        self.channel_id = config.channel_id

    async def post(self, message: str) -> None:
        payload = {
            "channel_id": self.channel_id,
            "message": message,
        }

        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/api/v4/posts",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
