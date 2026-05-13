import pytest

from sunbeam_valet.config import (
    AgentConfig,
    HarnessConfig,
    JudgeConfig,
    MattermostConfig,
    Round2TriggerConfig,
    RoutingConfig,
    WatchtowerConfig,
)


@pytest.fixture
def sample_agent_configs():
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


@pytest.fixture
def sample_judge_config():
    return JudgeConfig(
        name="judge",
        system_prompt="You are the judge.",
        model="openai/gpt-4o",
        consensus_threshold=0.7,
    )


@pytest.fixture
def sample_mattermost_config():
    return MattermostConfig(
        server_url="https://mattermost.example.com",
        bot_token="test-token",
        channel_id="test-channel-id",
    )


@pytest.fixture
def sample_watchtower_config():
    return WatchtowerConfig(
        command=["watchtower", "bugs", "--format", "json"],
        bug_filter={"status": ["New", "Confirmed"]},
    )


@pytest.fixture
def sample_harness_config(
    sample_agent_configs, sample_judge_config, sample_mattermost_config, sample_watchtower_config
):
    return HarnessConfig(
        agents=sample_agent_configs,
        judge=sample_judge_config,
        routing=RoutingConfig(),
        round2_trigger=Round2TriggerConfig(metric="std_dev", threshold=0.3),
        max_rounds=2,
        mattermost=sample_mattermost_config,
        watchtower=sample_watchtower_config,
    )
