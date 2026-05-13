from typing import Protocol

from sunbeam_valet.models import AgentOutput


class DisagreementMetric(Protocol):
    def compute(self, agent_outputs: list[AgentOutput]) -> float:
        raise NotImplementedError
