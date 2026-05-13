from dataclasses import dataclass
from typing import cast

from pydantic_ai import Agent, ModelRetry

from sunbeam_valet.config import AgentConfig
from sunbeam_valet.models import AgentAnalysis, AgentOutput, Bug


@dataclass
class AgentResult:
    output: AgentOutput | None
    error: str | None


async def run_agent(
    config: AgentConfig,
    bug: Bug,
    *,
    round_number: int,
    context: list[AgentOutput] | None = None,
) -> AgentResult:
    agent = Agent(
        config.model,
        output_type=AgentAnalysis,
        system_prompt=config.system_prompt,
    )

    prompt = _build_prompt(bug, context)

    try:
        result = await agent.run(prompt)
        output = _to_agent_output(
            config.name,
            round_number=round_number,
            output=cast(AgentAnalysis, result.output),
        )
        return AgentResult(output=output, error=None)
    except ModelRetry as e:
        return AgentResult(output=None, error=f"model retry: {e}")
    except Exception as e:
        return AgentResult(output=None, error=str(e))


def _build_prompt(bug: Bug, context: list[AgentOutput] | None = None) -> str:
    previous_outputs = ""
    if context:
        previous_outputs = f"{_build_other_agents_context(context)}\n\n"

    return f"""{previous_outputs}BUG TO ANALYZE:
Title: {bug.title}
Status: {bug.status}
Importance: {bug.importance}
Description: {bug.description}
URL: {bug.url}

Return a structured analysis with a verdict, confidence score, and concerns.
"""


def _to_agent_output(
    agent_name: str,
    *,
    round_number: int,
    output: AgentAnalysis,
) -> AgentOutput:
    return AgentOutput(
        agent_name=agent_name,
        round=round_number,
        verdict=output.verdict,
        confidence=output.confidence,
        concerns=output.concerns,
        raw_output=output.model_dump_json(),
    )


def _build_other_agents_context(outputs: list[AgentOutput]) -> str:
    lines = [
        "In the previous round, other agents provided their analysis.",
        "Review their findings and provide your updated assessment.",
        "",
        "OTHER AGENTS' ROUND 1 OUTPUTS:",
    ]
    for output in outputs:
        lines.append(f"  - {output.agent_name} (confidence={output.confidence}): {output.verdict}")
        if output.concerns:
            concerns = "; ".join(output.concerns)
            lines.append(f"    concerns: {concerns}")
    return "\n".join(lines)
