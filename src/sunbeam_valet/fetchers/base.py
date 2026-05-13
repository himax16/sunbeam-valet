from typing import Protocol

from sunbeam_valet.models import Bug


class BugFetcher(Protocol):
    async def fetch(self) -> list[Bug]:
        raise NotImplementedError
