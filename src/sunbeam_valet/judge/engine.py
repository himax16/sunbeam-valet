from typing import cast

from pydantic_ai import Agent, ModelRetry

from sunbeam_valet.config import JudgeConfig
from sunbeam_valet.models import AgentOutput, Bug, JudgeDecision, JudgeOutput


async def run_judge(
    config: JudgeConfig,
    bug: Bug,
    all_outputs: list[AgentOutput],
    did_round2: bool,
) -> JudgeOutput:
    agent = Agent(
        config.model,
        output_type=JudgeDecision,
        system_prompt=config.system_prompt,
    )

    prompt = _build_judge_prompt(bug, all_outputs, did_round2)

    try:
        result = await agent.run(prompt)
        decision = cast(JudgeDecision, result.output)

        return JudgeOutput(
            bug_id=bug.id,
            summary=decision.summary,
            confidence=decision.confidence,
            agent_votes={o.agent_name: o.confidence for o in all_outputs},
            status="round2" if did_round2 else "ok",
            did_round2=did_round2,
            error=None,
        )
    except ModelRetry as e:
        return _error_output(bug.id, f"model retry: {e}", all_outputs, did_round2)
    except Exception as e:
        return _error_output(bug.id, str(e), all_outputs, did_round2)


def _build_judge_prompt(bug: Bug, outputs: list[AgentOutput], did_round2: bool) -> str:
    lines = [
        "BUG UNDER REVIEW:",
        f"Title: {bug.title}",
        f"Status: {bug.status}",
        f"Importance: {bug.importance}",
        f"Description: {bug.description}",
        f"URL: {bug.url}",
        "",
        "AGENT ANALYSES:",
    ]

    for output in outputs:
        lines.append(f"\n--- {output.agent_name} (Round {output.round}) ---")
        lines.append(f"Confidence: {output.confidence}")
        lines.append(f"Verdict: {output.verdict}")
        if output.concerns:
            lines.append(f"Concerns: {', '.join(output.concerns)}")

    lines.append("")
    lines.append(
        "As the judge, merge these analyses into a structured decision with "
        "a summary, confidence score, and prioritized concerns."
    )

    if did_round2:
        lines.append("\nNote: A second round of debate occurred. Consider the updated positions.")

    return "\n".join(lines)


def _error_output(
    bug_id: str,
    error: str,
    outputs: list[AgentOutput],
    did_round2: bool,
) -> JudgeOutput:
    return JudgeOutput(
        bug_id=bug_id,
        summary="ERROR",
        confidence=0.0,
        agent_votes={o.agent_name: o.confidence for o in outputs} if outputs else {},
        status="error",
        did_round2=did_round2,
        error=error,
    )
