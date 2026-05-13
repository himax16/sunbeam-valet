from typing import Literal

from pydantic import BaseModel, Field


class Bug(BaseModel):
    id: str
    title: str
    status: str
    importance: str
    description: str
    url: str
    source: Literal["launchpad"] = "launchpad"


class AgentOutput(BaseModel):
    agent_name: str
    round: int
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    concerns: list[str] = Field(default_factory=list)
    raw_output: str


class AgentAnalysis(BaseModel):
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    concerns: list[str] = Field(default_factory=list)


class JudgeDecision(BaseModel):
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    classification: Literal[
        "bug",
        "feature request",
        "security issue",
        "operational issue",
        "other",
    ]
    priority: Literal["critical", "high", "medium", "low"]
    action: Literal[
        "fix immediately",
        "hotfix",
        "next release",
        "backlog",
        "monitor",
        "close/wontfix",
        "other",
    ]
    rationale: str
    concerns: list[str] = Field(default_factory=list)


class JudgeOutput(BaseModel):
    bug_id: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    classification: str | None
    priority: str | None
    action: str | None
    rationale: str | None
    concerns: list[str] = Field(default_factory=list)
    agent_votes: dict[str, float]
    status: Literal["ok", "error", "round2"]
    did_round2: bool
    error: str | None = None


class TableRow(BaseModel):
    bug_reference: str
    bug_reference_url: str
    summary: str
    confidence: float | None
    classification: str | None
    priority: str | None
    action: str | None
    agent_votes: dict[str, float]
    status: Literal["ok", "error", "round2"]
    round2: bool
