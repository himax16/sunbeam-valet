import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal[
    "new",
    "triaging",
    "triaged",
    "accepted",
    "rejected",
    "New",
    "Fix Released",
    "Fix Committed",
    "In Progress",
    "Confirmed",
    "Triaged",
    "Invalid",
    "Won't Fix",
    "Opinion",
    "Incomplete",
    "Expired",
]
Classification = Literal["bug", "feature", "security", "other"]
Priority = Literal["critical", "high", "medium", "low"]
BugSource = Literal["launchpad", "github", "jira", "manual", "other"]


class Bug(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: str = ""
    source: BugSource = "manual"
    url: str = ""
    importance: str = ""
    status: str = "new"
    classification: Classification | None = None
    priority: Priority | None = None
    action: str | None = None
    rationale: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
