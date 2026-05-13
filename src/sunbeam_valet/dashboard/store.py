import logging

from sunbeam_valet.dashboard.models import Bug

logger = logging.getLogger(__name__)


class InMemoryBugStore:
    def __init__(self) -> None:
        self._bugs: dict[str, Bug] = {}

    def list_all(self) -> list[Bug]:
        return sorted(
            self._bugs.values(),
            key=lambda b: (
                {"new": 0, "triaged": 1, "accepted": 2, "rejected": 3, "triaging": 4}.get(
                    b.status, 9
                ),
                b.id,
            ),
        )

    def get(self, bug_id: str) -> Bug | None:
        return self._bugs.get(bug_id)

    def add(self, bug: Bug) -> None:
        self._bugs[bug.id] = bug

    def update(self, bug: Bug) -> None:
        self._bugs[bug.id] = bug

    def replace_all(self, bugs: list[Bug]) -> None:
        self._bugs = {b.id: b for b in bugs}

    def load_from_db(self) -> int:
        from sunbeam_valet.dashboard import db as dashboard_db

        try:
            rows = dashboard_db.list_bugs(limit=500)
        except Exception:
            logger.debug("Could not load bugs from DB (table may not exist yet)")
            return 0
        self._bugs.clear()
        for row in rows:
            bug = Bug(
                id=row["id"],
                title=row["title"],
                description=row.get("description", ""),
                url=row.get("url", ""),
                importance=row.get("importance", ""),
                source=row.get("source", "launchpad"),
                status=row.get("status", "new"),
            )
            self._bugs[bug.id] = bug
        return len(self._bugs)


_store = InMemoryBugStore()
_store.load_from_db()


def get_store() -> InMemoryBugStore:
    return _store
