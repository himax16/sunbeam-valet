import statistics

from sunbeam_valet.models import AgentOutput


class StdDevDisagreementMetric:
    name: str = "std_dev"

    def compute(self, agent_outputs: list[AgentOutput]) -> float:
        if len(agent_outputs) < 2:
            return 0.0
        confidences = [output.confidence for output in agent_outputs]
        return statistics.stdev(confidences)
