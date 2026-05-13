from unittest.mock import AsyncMock, patch

import pytest

from sunbeam_valet.config import JudgeConfig
from sunbeam_valet.judge.engine import run_judge
from sunbeam_valet.models import AgentOutput, Bug, JudgeDecision


@pytest.fixture
def judge_config():
    return JudgeConfig(name="judge", system_prompt="Merge analyses.", model="openai/gpt-4o")


@pytest.fixture
def bug():
    return Bug(
        id="123",
        title="Test bug",
        status="New",
        importance="High",
        description="Something failed.",
        url="https://bugs.launchpad.net/bugs/123",
    )


@pytest.fixture
def agent_outputs():
    return [
        AgentOutput(
            agent_name="security",
            round=1,
            verdict="security concern",
            confidence=0.8,
            concerns=["needs reproducer"],
            raw_output="",
        )
    ]


@pytest.mark.asyncio
async def test_run_judge_merges_agent_outputs(judge_config, bug, agent_outputs):
    with patch("sunbeam_valet.judge.engine.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = AsyncMock(
            output=JudgeDecision(
                summary="Needs maintainer review",
                confidence=0.75,
                concerns=["needs reproducer"],
            )
        )
        mock_agent_class.return_value = mock_agent

        result = await run_judge(judge_config, bug, agent_outputs, did_round2=False)

    assert result.bug_id == "123"
    assert result.summary == "Needs maintainer review"
    assert result.confidence == 0.75
    assert result.concerns == ["needs reproducer"]
    assert result.agent_votes == {"security": 0.8}
    assert result.status == "ok"


@pytest.mark.asyncio
async def test_run_judge_marks_round2_status(judge_config, bug, agent_outputs):
    with patch("sunbeam_valet.judge.engine.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = AsyncMock(
            output=JudgeDecision(summary="Updated", confidence=0.65)
        )
        mock_agent_class.return_value = mock_agent

        result = await run_judge(judge_config, bug, agent_outputs, did_round2=True)

    assert result.status == "round2"
    assert result.did_round2 is True


@pytest.mark.asyncio
async def test_run_judge_returns_error_output(judge_config, bug, agent_outputs):
    with patch("sunbeam_valet.judge.engine.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("judge failed")
        mock_agent_class.return_value = mock_agent

        result = await run_judge(judge_config, bug, agent_outputs, did_round2=False)

    assert result.status == "error"
    assert result.error == "judge failed"
    assert result.agent_votes == {"security": 0.8}
