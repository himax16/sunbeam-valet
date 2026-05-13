import asyncio
from dataclasses import dataclass

from sunbeam_valet.agent.runner import AgentResult, run_agent, run_agent_with_context
from sunbeam_valet.config import AgentConfig
from sunbeam_valet.models import AgentOutput, Bug


@dataclass
class RoundResult:
    outputs: list[AgentOutput]
    errors: dict[str, str]


class AgentPool:
    def __init__(self, agent_configs: list[AgentConfig]):
        self.agents = {cfg.name: cfg for cfg in agent_configs}

    async def run_round1(
        self,
        bug: Bug,
    ) -> RoundResult:
        tasks = [run_agent(config, bug, "") for config in self.agents.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._collect_results(results, round=1)

    async def run_round2(
        self,
        bug: Bug,
        round1_outputs: list[AgentOutput],
    ) -> RoundResult:
        tasks = [
            run_agent_with_context(config, bug, round1_outputs) for config in self.agents.values()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._collect_results(results, round=2)

    def _collect_results(
        self,
        results: list[AgentResult | BaseException],
        round: int,
    ) -> RoundResult:
        outputs = []
        errors = {}

        for i, result in enumerate(results):
            agent_name = list(self.agents.values())[i].name

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
                output = result.output
                output.round = round
                outputs.append(output)
            else:
                errors[agent_name] = "no output returned"

        return RoundResult(outputs=outputs, errors=errors)
