import asyncio
import json
from typing import Any

from sunbeam_valet.config import WatchtowerConfig
from sunbeam_valet.models import Bug


class WatchtowerFetcher:
    def __init__(self, config: WatchtowerConfig):
        self.command = config.command
        self.bug_filter = config.bug_filter

    async def fetch(self) -> list[Bug]:
        proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"watchtower command failed: {stderr.decode()}")

        raw = json.loads(stdout.decode())
        if not isinstance(raw, list):
            raise ValueError("watchtower command must return a JSON list")

        bugs = [self._parse_bug(item) for item in raw]
        return self._filter_bugs(bugs)

    def _parse_bug(self, raw: dict[str, Any]) -> Bug:
        return Bug(
            id=raw.get("id", ""),
            title=raw.get("title", ""),
            status=raw.get("status", ""),
            importance=raw.get("importance", ""),
            description=raw.get("description", ""),
            url=raw.get("url", ""),
            source=raw.get("source", "launchpad"),
        )

    def _filter_bugs(self, bugs: list[Bug]) -> list[Bug]:
        if not self.bug_filter:
            return bugs

        statuses = self.bug_filter.get("status", [])
        if not statuses:
            return bugs

        return [b for b in bugs if b.status in statuses]
