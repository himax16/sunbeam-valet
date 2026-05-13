import asyncio
from dataclasses import dataclass

from sunbeam_valet.agent.runner import AgentResult, run_agent
from sunbeam_valet.config import AgentConfig
from sunbeam_valet.models import AgentOutput, Bug


@dataclass
class RoundResult:
    outputs: list[AgentOutput]
    errors: dict[str, str]


class AgentPool:
    def __init__(self, agent_configs: list[AgentConfig]):
        self.agents = list(agent_configs)

    async def run_agents(
        self,
        bug: Bug,
        *,
        round_number: int,
        context: list[AgentOutput] | None = None,
    ) -> RoundResult:
        tasks = [
            run_agent(config, bug, round_number=round_number, context=context)
            for config in self.agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._collect_results(results)

    def _collect_results(
        self,
        results: list[AgentResult | BaseException],
    ) -> RoundResult:
        outputs = []
        errors = {}

        for config, result in zip(self.agents, results, strict=True):
            agent_name = config.name

            if isinstance(result, BaseException):
                errors[agent_name] = str(result)
                continue

            if not isinstance(result, AgentResult):
                errors[agent_name] = f"unexpected result type: {type(result)}"
                continue

            if result.error:
                errors[agent_name] = result.error
                continue

            if result.output:
                outputs.append(result.output)
            else:
                errors[agent_name] = "no output returned"

        return RoundResult(outputs=outputs, errors=errors)
