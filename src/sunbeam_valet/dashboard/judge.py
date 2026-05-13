import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """\
You are a bug triage judge. Review the bug report and provide a verdict.

Output a JSON object with:
- verdict: "critical", "high", "medium", "low", "wontfix", or "invalid"
- confidence: 0.0 to 1.0
- summary: a 1-2 sentence summary of your decision
- concerns: list of specific concerns or action items
"""


class JudgeOutput(BaseModel):
    verdict: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = ""
    concerns: list[str] = Field(default_factory=list)


async def run_judge(
    bug_id: str,
    bug_title: str,
    bug_description: str,
    bug_source: str = "launchpad",
    bug_status: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    try:
        from pydantic_ai import Agent

        agent = Agent(
            model or "openai/gpt-4o-mini",
            output_type=JudgeOutput,
            system_prompt=JUDGE_SYSTEM_PROMPT,
        )

        prompt = (
            f"BUG ID: {bug_id}\n"
            f"Title: {bug_title}\n"
            f"Source: {bug_source}\n"
            f"Status: {bug_status}\n"
            f"Description: {bug_description}\n"
        )

        result = await agent.run(prompt)
        output = result.output

        verdict = output.verdict if isinstance(output, JudgeOutput) else "unknown"
        confidence = output.confidence if isinstance(output, JudgeOutput) else 0.0
        summary = output.summary if isinstance(output, JudgeOutput) else ""
        concerns = output.concerns if isinstance(output, JudgeOutput) else []
        raw_output = (
            json.dumps(output.model_dump()) if isinstance(output, JudgeOutput) else str(result)
        )

        from sunbeam_valet.dashboard import db as dashboard_db

        dashboard_db.save_judgement(
            bug_id=bug_id,
            bug_title=bug_title,
            bug_description=bug_description,
            bug_source=bug_source,
            verdict=verdict,
            confidence=confidence,
            summary=summary,
            concerns=concerns,
            raw_output=raw_output,
        )

        return {
            "success": True,
            "verdict": verdict,
            "confidence": confidence,
            "summary": summary,
            "concerns": concerns,
        }
    except Exception as exc:
        logger.exception("Judge AI query failed for bug %s", bug_id)
        return {
            "success": False,
            "error": str(exc),
        }


async def demo_judge(
    bug_id: str,
    bug_title: str,
    bug_description: str,
    bug_source: str = "launchpad",
) -> dict[str, Any]:
    logger.warning("No AI model available; using demo judge for bug %s", bug_id)

    verdict = "medium"
    if "critical" in bug_title.lower() or "security" in bug_title.lower():
        verdict = "high"
    elif "typo" in bug_title.lower() or "cosmetic" in bug_title.lower():
        verdict = "low"

    await asyncio.sleep(0.5)

    from sunbeam_valet.dashboard import db as dashboard_db

    dashboard_db.save_judgement(
        bug_id=bug_id,
        bug_title=bug_title,
        bug_description=bug_description,
        bug_source=bug_source,
        verdict=verdict,
        confidence=0.8,
        summary=f"Demo judgement: {verdict} severity for this bug.",
        concerns=["Review for completeness", "Check for upstream duplicates"],
        raw_output=f"DEMO: verdict={verdict}",
    )

    return {
        "success": True,
        "verdict": verdict,
        "confidence": 0.8,
        "summary": f"Demo judgement: {verdict} severity.",
        "concerns": ["Review for completeness", "Check for upstream duplicates"],
    }
