from typing import Literal

from pydantic import BaseModel


class MergedConcern(BaseModel):
    text: str
    priority: Literal["high", "medium", "low"]
    sources: list[str]


class MergeResult(BaseModel):
    summary: str
    concerns: list[MergedConcern]
    final_confidence: float
