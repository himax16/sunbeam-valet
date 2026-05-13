import pytest

from sunbeam_valet.disagreement import get_metric
from sunbeam_valet.disagreement.std_dev import StdDevDisagreementMetric
from sunbeam_valet.models import AgentOutput


class TestStdDevDisagreementMetric:
    def test_empty_list_returns_zero(self):
        metric = StdDevDisagreementMetric()
        assert metric.compute([]) == 0.0

    def test_single_agent_returns_zero(self):
        metric = StdDevDisagreementMetric()
        output = AgentOutput(
            agent_name="test",
            round=1,
            verdict="test verdict",
            confidence=0.8,
            concerns=[],
            raw_output="raw",
        )
        assert metric.compute([output]) == 0.0

    def test_identical_confidences_returns_zero(self):
        metric = StdDevDisagreementMetric()
        outputs = [
            AgentOutput(
                agent_name="a", round=1, verdict="v", confidence=0.7, concerns=[], raw_output=""
            ),
            AgentOutput(
                agent_name="b", round=1, verdict="v", confidence=0.7, concerns=[], raw_output=""
            ),
        ]
        assert metric.compute(outputs) == 0.0

    def test_different_confidences_returns_nonzero(self):
        metric = StdDevDisagreementMetric()
        outputs = [
            AgentOutput(
                agent_name="a", round=1, verdict="v", confidence=0.9, concerns=[], raw_output=""
            ),
            AgentOutput(
                agent_name="b", round=1, verdict="v", confidence=0.5, concerns=[], raw_output=""
            ),
        ]
        result = metric.compute(outputs)
        assert result > 0.0


class TestGetMetric:
    def test_get_std_dev(self):
        metric = get_metric("std_dev")
        assert isinstance(metric, StdDevDisagreementMetric)

    def test_unknown_metric_raises(self):
        with pytest.raises(ValueError):
            get_metric("unknown")
