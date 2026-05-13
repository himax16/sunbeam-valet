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
    system_context: str,
) -> AgentResult:
    agent = Agent(
        config.model,
        output_type=AgentAnalysis,
        system_prompt=config.system_prompt,
    )

    prompt = _build_prompt(bug, system_context)

    try:
        result = await agent.run(prompt)
        output = _to_agent_output(config.name, cast(AgentAnalysis, result.output))
        return AgentResult(output=output, error=None)
    except ModelRetry as e:
        return AgentResult(output=None, error=f"model retry: {e}")
    except Exception as e:
        return AgentResult(output=None, error=str(e))


def _build_prompt(bug: Bug, system_context: str = "") -> str:
    context = f"{system_context}\n\n" if system_context else ""
    return f"""{context}BUG TO ANALYZE:
Title: {bug.title}
Status: {bug.status}
Importance: {bug.importance}
Description: {bug.description}
URL: {bug.url}

Return a structured analysis with a verdict, confidence score, and concerns.
"""


def _to_agent_output(
    agent_name: str,
    output: AgentAnalysis,
) -> AgentOutput:
    return AgentOutput(
        agent_name=agent_name,
        round=1,
        verdict=output.verdict,
        confidence=output.confidence,
        concerns=output.concerns,
        raw_output=output.model_dump_json(),
    )


async def run_agent_with_context(
    config: AgentConfig,
    bug: Bug,
    round1_outputs: list[AgentOutput],
) -> AgentResult:
    other_agents_context = _build_other_agents_context(round1_outputs)

    system_context = (
        f"{config.system_prompt}\n\n"
        "In the previous round, other agents provided their analysis. "
        "Review their findings and provide your updated assessment.\n\n"
        f"{other_agents_context}"
    )

    return await run_agent(config, bug, system_context)


def _build_other_agents_context(outputs: list[AgentOutput]) -> str:
    lines = ["OTHER AGENTS' ROUND 1 OUTPUTS:"]
    for output in outputs:
        lines.append(f"  - {output.agent_name} (confidence={output.confidence}): {output.verdict}")
    return "\n".join(lines)
