from unittest.mock import AsyncMock, patch

import pytest

from sunbeam_valet.agent.pool import AgentPool
from sunbeam_valet.config import AgentConfig
from sunbeam_valet.harness import Harness
from sunbeam_valet.models import AgentAnalysis, AgentOutput, Bug, JudgeDecision


@pytest.fixture
def mock_bug():
    return Bug(
        id="12345",
        title="Test bug for integration",
        status="New",
        importance="Medium",
        description="This is a test bug description.",
        url="https://bugs.launchpad.net/bugs/12345",
        source="launchpad",
    )


@pytest.fixture
def mock_agent_configs():
    return [
        AgentConfig(
            name="security_expert",
            system_prompt="You are a security expert.",
            model="openai/gpt-4o",
        ),
        AgentConfig(
            name="triage_specialist",
            system_prompt="You are a triage specialist.",
            model="openai/gpt-4o-mini",
        ),
    ]


class TestAgentPool:
    @pytest.mark.asyncio
    async def test_run_round1_returns_outputs(self, mock_bug, mock_agent_configs):
        pool = AgentPool(mock_agent_configs)
        with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_agent.run.return_value = AsyncMock(
                output=AgentAnalysis(
                    verdict="Test verdict",
                    confidence=0.8,
                    concerns=[],
                ),
            )

            result = await pool.run_round1(mock_bug)
            assert len(result.outputs) == 2
            assert result.errors == {}

    @pytest.mark.asyncio
    async def test_run_round1_handles_errors(self, mock_bug, mock_agent_configs):
        pool = AgentPool(mock_agent_configs)
        with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_agent.run.side_effect = [
                Exception("API error"),
                AsyncMock(
                    output=AgentAnalysis(
                        verdict="ok",
                        confidence=0.5,
                        concerns=[],
                    ),
                ),
            ]

            result = await pool.run_round1(mock_bug)
            assert len(result.outputs) == 1
            assert "security_expert" in result.errors


class TestHarness:
    @pytest.mark.asyncio
    async def test_process_bug_round1_only(self, mock_bug, sample_harness_config):
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_round1", new_callable=AsyncMock) as mock_r1:
            mock_r1.return_value.outputs = [
                AgentOutput(
                    agent_name="sec",
                    round=1,
                    verdict="v1",
                    confidence=0.9,
                    concerns=[],
                    raw_output="",
                ),
                AgentOutput(
                    agent_name="tri",
                    round=1,
                    verdict="v2",
                    confidence=0.85,
                    concerns=[],
                    raw_output="",
                ),
            ]
            mock_r1.return_value.errors = {}

            with patch("sunbeam_valet.judge.engine.Agent") as mock_judge_agent:
                mock_judge = AsyncMock()
                mock_judge_agent.return_value = mock_judge
                mock_judge.run.return_value = AsyncMock(
                    output=JudgeDecision(
                        summary="Merged verdict",
                        confidence=0.87,
                        concerns=[],
                    ),
                )

                row = await harness._process_bug(mock_bug)

        assert row.bug_reference == "LP:#12345"
        assert row.round2 == "no"

    @pytest.mark.asyncio
    async def test_process_bug_triggers_round2_on_disagreement(
        self, mock_bug, sample_harness_config
    ):
        sample_harness_config.round2_trigger.threshold = 0.05
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_round1", new_callable=AsyncMock) as mock_r1:
            mock_r1.return_value.outputs = [
                AgentOutput(
                    agent_name="sec",
                    round=1,
                    verdict="v1",
                    confidence=0.9,
                    concerns=[],
                    raw_output="",
                ),
                AgentOutput(
                    agent_name="tri",
                    round=1,
                    verdict="v2",
                    confidence=0.3,
                    concerns=[],
                    raw_output="",
                ),
            ]
            mock_r1.return_value.errors = {}

            with patch.object(harness.pool, "run_round2", new_callable=AsyncMock) as mock_r2:
                mock_r2.return_value.outputs = [
                    AgentOutput(
                        agent_name="sec",
                        round=2,
                        verdict="v1-updated",
                        confidence=0.85,
                        concerns=[],
                        raw_output="",
                    ),
                    AgentOutput(
                        agent_name="tri",
                        round=2,
                        verdict="v2-updated",
                        confidence=0.4,
                        concerns=[],
                        raw_output="",
                    ),
                ]
                mock_r2.return_value.errors = {}

                with patch("sunbeam_valet.judge.engine.Agent") as mock_judge_agent:
                    mock_judge = AsyncMock()
                    mock_judge_agent.return_value = mock_judge
                    mock_judge.run.return_value = AsyncMock(
                        output=JudgeDecision(
                            summary="Merged after debate",
                            confidence=0.65,
                            concerns=[],
                        ),
                    )

                    row = await harness._process_bug(mock_bug)

        assert row.round2 == "yes"

    @pytest.mark.asyncio
    async def test_process_bug_skips_round2_when_max_rounds_is_one(
        self, mock_bug, sample_harness_config
    ):
        sample_harness_config.max_rounds = 1
        sample_harness_config.round2_trigger.threshold = 0.05
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_round1", new_callable=AsyncMock) as mock_r1:
            mock_r1.return_value.outputs = [
                AgentOutput(
                    agent_name="sec",
                    round=1,
                    verdict="v1",
                    confidence=0.9,
                    concerns=[],
                    raw_output="",
                ),
                AgentOutput(
                    agent_name="tri",
                    round=1,
                    verdict="v2",
                    confidence=0.3,
                    concerns=[],
                    raw_output="",
                ),
            ]
            mock_r1.return_value.errors = {}

            with (
                patch.object(harness.pool, "run_round2", new_callable=AsyncMock) as mock_r2,
                patch("sunbeam_valet.judge.engine.Agent") as mock_judge_agent,
            ):
                mock_judge = AsyncMock()
                mock_judge_agent.return_value = mock_judge
                mock_judge.run.return_value = AsyncMock(
                    output=JudgeDecision(
                        summary="Merged without debate",
                        confidence=0.65,
                        concerns=[],
                    ),
                )

                row = await harness._process_bug(mock_bug)

        assert row.round2 == "no"
        mock_r2.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_bug_error_propagates(self, mock_bug, sample_harness_config):
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_round1", new_callable=AsyncMock) as mock_r1:
            mock_r1.return_value.outputs = []
            mock_r1.return_value.errors = {"sec": "API timeout"}

            with patch("sunbeam_valet.judge.engine.Agent") as mock_judge_agent:
                mock_judge = AsyncMock()
                mock_judge_agent.return_value = mock_judge
                mock_judge.run.return_value = AsyncMock(
                    output=JudgeDecision(
                        summary="Error handling",
                        confidence=0.5,
                        concerns=[],
                    ),
                )

                row = await harness._process_bug(mock_bug)

        assert row.status == "error"
        assert row.confidence == "ERROR"
