from typing import Protocol

from sunbeam_valet.models import TableRow


class OutputFormatter(Protocol):
    def format(self, rows: list[TableRow], round2_count: int) -> str:
        raise NotImplementedError
