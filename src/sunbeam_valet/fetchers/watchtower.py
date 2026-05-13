import asyncio
import json
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, ValidationError

from sunbeam_valet.config import WatchtowerConfig
from sunbeam_valet.models import Bug


class WatchtowerBugPayload(BaseModel):
    id: str = Field(validation_alias=AliasChoices("id", "bug_id"), min_length=1)
    title: str = Field(min_length=1)
    status: str = Field(min_length=1)
    importance: str = Field(min_length=1)
    description: str | None = None
    url: str = Field(min_length=1)
    source: Literal["launchpad"] = "launchpad"


class WatchtowerFetcher:
    def __init__(self, config: WatchtowerConfig):
        self.command = config.command
        self.status_filter = config.bug_filter.status

    async def fetch(self) -> list[Bug]:
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"watchtower command failed: {stderr.decode()}")

        try:
            raw = json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise ValueError("watchtower command returned invalid JSON") from exc

        if not isinstance(raw, list):
            raise ValueError("watchtower command must return a JSON list")

        bugs = [self._parse_bug(item, index) for index, item in enumerate(raw)]
        return self._filter_bugs(bugs)

    def _parse_bug(self, raw: object, index: int) -> Bug:
        try:
            payload = WatchtowerBugPayload.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"invalid watchtower bug at index {index}") from exc

        return Bug(
            id=payload.id,
            title=payload.title,
            status=payload.status,
            importance=payload.importance,
            description=payload.description or payload.title,
            url=payload.url,
            source=payload.source,
        )

    def _filter_bugs(self, bugs: list[Bug]) -> list[Bug]:
        if not self.status_filter:
            return bugs

        return [b for b in bugs if b.status in self.status_filter]
