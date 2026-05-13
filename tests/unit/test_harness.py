from unittest.mock import AsyncMock, patch

import pytest

from sunbeam_valet.agent.pool import AgentPool, RoundResult
from sunbeam_valet.config import AgentConfig
from sunbeam_valet.harness import Harness
from sunbeam_valet.models import AgentAnalysis, AgentOutput, Bug, JudgeDecision, JudgeOutput


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
    async def test_run_agents_returns_outputs_for_round(self, mock_bug, mock_agent_configs):
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

            result = await pool.run_agents(mock_bug, round_number=1)
            assert len(result.outputs) == 2
            assert {output.round for output in result.outputs} == {1}
            assert result.errors == {}

    @pytest.mark.asyncio
    async def test_run_agents_handles_errors(self, mock_bug, mock_agent_configs):
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

            result = await pool.run_agents(mock_bug, round_number=1)
            assert len(result.outputs) == 1
            assert "security_expert" in result.errors

    @pytest.mark.asyncio
    async def test_run_agents_uses_context_for_later_rounds(self, mock_bug, mock_agent_configs):
        pool = AgentPool(mock_agent_configs)
        round1_outputs = [
            AgentOutput(
                agent_name="security_expert",
                round=1,
                verdict="needs more info",
                confidence=0.4,
                concerns=[],
                raw_output="",
            )
        ]

        with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_agent.run.return_value = AsyncMock(
                output=AgentAnalysis(
                    verdict="updated",
                    confidence=0.7,
                    concerns=[],
                ),
            )

            result = await pool.run_agents(
                mock_bug,
                round_number=2,
                context=round1_outputs,
            )

        assert len(result.outputs) == 2
        assert {output.round for output in result.outputs} == {2}
        prompts = [call.args[0] for call in mock_agent.run.await_args_list]
        assert all("OTHER AGENTS' ROUND 1 OUTPUTS" in prompt for prompt in prompts)


class TestHarness:
    @pytest.mark.asyncio
    async def test_process_bug_round1_only(self, mock_bug, sample_harness_config):
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_agents", new_callable=AsyncMock) as mock_run_agents:
            mock_run_agents.return_value = RoundResult(
                outputs=[
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
                ],
                errors={},
            )

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

                row = await harness._triage_bug(mock_bug)

        assert row.bug_reference == "LP:#12345"
        assert row.round2 is False
        mock_run_agents.assert_awaited_once_with(mock_bug, round_number=1)

    @pytest.mark.asyncio
    async def test_process_bug_triggers_round2_on_disagreement(
        self, mock_bug, sample_harness_config
    ):
        sample_harness_config.round2_trigger.threshold = 0.05
        harness = Harness(sample_harness_config)

        round1_outputs = [
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
        with patch.object(harness.pool, "run_agents", new_callable=AsyncMock) as mock_run_agents:
            mock_run_agents.side_effect = [
                RoundResult(outputs=round1_outputs, errors={}),
                RoundResult(
                    outputs=[
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
                    ],
                    errors={},
                ),
            ]

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

                row = await harness._triage_bug(mock_bug)

        assert row.round2 is True
        assert mock_run_agents.await_args_list[0].kwargs == {"round_number": 1}
        assert mock_run_agents.await_args_list[1].kwargs == {
            "round_number": 2,
            "context": round1_outputs,
        }

    @pytest.mark.asyncio
    async def test_process_bug_skips_round2_when_max_rounds_is_one(
        self, mock_bug, sample_harness_config
    ):
        sample_harness_config.max_rounds = 1
        sample_harness_config.round2_trigger.threshold = 0.05
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_agents", new_callable=AsyncMock) as mock_run_agents:
            mock_run_agents.return_value = RoundResult(
                outputs=[
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
                ],
                errors={},
            )

            with patch("sunbeam_valet.judge.engine.Agent") as mock_judge_agent:
                mock_judge = AsyncMock()
                mock_judge_agent.return_value = mock_judge
                mock_judge.run.return_value = AsyncMock(
                    output=JudgeDecision(
                        summary="Merged without debate",
                        confidence=0.65,
                        concerns=[],
                    ),
                )

                row = await harness._triage_bug(mock_bug)

        assert row.round2 is False
        mock_run_agents.assert_awaited_once_with(mock_bug, round_number=1)

    @pytest.mark.asyncio
    async def test_process_bug_error_propagates(self, mock_bug, sample_harness_config):
        harness = Harness(sample_harness_config)

        with patch.object(harness.pool, "run_agents", new_callable=AsyncMock) as mock_run_agents:
            mock_run_agents.return_value = RoundResult(
                outputs=[],
                errors={"sec": "API timeout"},
            )

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

                row = await harness._triage_bug(mock_bug)

        assert row.status == "error"
        assert row.confidence is None

    @pytest.mark.asyncio
    async def test_run_fetches_triages_formats_and_posts(self, mock_bug, sample_harness_config):
        harness = Harness(sample_harness_config)
        row = harness._to_table_row(
            mock_bug,
            JudgeOutput(
                bug_id=mock_bug.id,
                summary="Merged",
                confidence=0.8,
                concerns=[],
                agent_votes={"sec": 0.8},
                status="ok",
                did_round2=False,
            ),
        )

        with (
            patch.object(harness.fetcher, "fetch", new_callable=AsyncMock) as mock_fetch,
            patch.object(harness, "_triage_bug", new_callable=AsyncMock) as mock_triage,
            patch.object(harness.poster, "post", new_callable=AsyncMock) as mock_post,
        ):
            mock_fetch.return_value = [mock_bug]
            mock_triage.return_value = row

            await harness.run()

        mock_fetch.assert_awaited_once_with()
        mock_triage.assert_awaited_once_with(mock_bug)
        mock_post.assert_awaited_once()
        posted_message = mock_post.call_args.args[0]
        assert "LP:#12345" in posted_message
        assert "Merged" in posted_message
