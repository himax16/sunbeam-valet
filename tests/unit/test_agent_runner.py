from unittest.mock import AsyncMock, patch

import pytest

from sunbeam_valet.agent.runner import run_agent
from sunbeam_valet.config import AgentConfig
from sunbeam_valet.models import AgentAnalysis, AgentOutput, Bug


@pytest.fixture
def agent_config():
    return AgentConfig(name="triage", system_prompt="Analyze the bug.", model="openai/gpt-4o")


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


@pytest.mark.asyncio
async def test_run_agent_returns_structured_output(agent_config, bug):
    with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = AsyncMock(
            output=AgentAnalysis(verdict="needs investigation", confidence=0.7)
        )
        mock_agent_class.return_value = mock_agent

        result = await run_agent(agent_config, bug, round_number=1)

    assert result.error is None
    assert result.output is not None
    assert result.output.agent_name == "triage"
    assert result.output.round == 1
    assert result.output.verdict == "needs investigation"


@pytest.mark.asyncio
async def test_run_agent_round2_prompt_includes_prior_concerns(agent_config, bug):
    context = [
        AgentOutput(
            agent_name="security",
            round=1,
            verdict="looks risky",
            confidence=0.4,
            concerns=["missing logs", "unclear impact"],
            raw_output="",
        )
    ]

    with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.return_value = AsyncMock(
            output=AgentAnalysis(verdict="updated", confidence=0.8)
        )
        mock_agent_class.return_value = mock_agent

        await run_agent(agent_config, bug, round_number=2, context=context)

    prompt = mock_agent.run.await_args.args[0]
    assert "missing logs" in prompt
    assert "unclear impact" in prompt


@pytest.mark.asyncio
async def test_run_agent_returns_error_for_model_exception(agent_config, bug):
    with patch("sunbeam_valet.agent.runner.Agent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.run.side_effect = RuntimeError("transport failed")
        mock_agent_class.return_value = mock_agent

        result = await run_agent(agent_config, bug, round_number=1)

    assert result.output is None
    assert result.error == "transport failed"
