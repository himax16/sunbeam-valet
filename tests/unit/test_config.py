from pathlib import Path

import pytest
from pydantic import ValidationError

from sunbeam_valet.config import HarnessConfig, load_config


def test_load_config_substitutes_required_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("MATTERMOST_URL", "https://mattermost.example.com")
    monkeypatch.setenv("MATTERMOST_BOT_TOKEN", "test-token")
    monkeypatch.setenv("MATTERMOST_CHANNEL_ID", "channel-id")

    config_path = tmp_path / "harness.yaml"
    config_path.write_text(
        """
agents:
  - name: triage
    system_prompt: Prompt
    model: openai/gpt-4o-mini
judge:
  name: judge
  system_prompt: Judge prompt
  model: openai/gpt-4o
mattermost:
  server_url: "${MATTERMOST_URL}"
  bot_token: "${MATTERMOST_BOT_TOKEN}"
  channel_id: "${MATTERMOST_CHANNEL_ID}"
watchtower:
  command: ["watchtower", "bugs", "--format", "json"]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.mattermost.server_url == "https://mattermost.example.com"
    assert config.mattermost.bot_token == "test-token"
    assert config.mattermost.channel_id == "channel-id"


def test_load_config_rejects_missing_environment_value(tmp_path):
    config_path = tmp_path / "harness.yaml"
    config_path.write_text(
        """
agents:
  - name: triage
    system_prompt: Prompt
    model: openai/gpt-4o-mini
judge:
  name: judge
  system_prompt: Judge prompt
  model: openai/gpt-4o
mattermost:
  server_url: "${MATTERMOST_URL}"
  bot_token: token
  channel_id: channel-id
watchtower:
  command: ["watchtower"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="MATTERMOST_URL"):
        load_config(config_path)


def test_harness_config_rejects_duplicate_agent_names(sample_harness_config):
    payload = sample_harness_config.model_dump()
    payload["agents"][1]["name"] = payload["agents"][0]["name"]

    with pytest.raises(ValidationError, match="unique"):
        HarnessConfig.model_validate(payload)


def test_harness_config_rejects_unsupported_max_rounds(sample_harness_config):
    payload = sample_harness_config.model_dump()
    payload["max_rounds"] = 3

    with pytest.raises(ValidationError, match="1 or 2"):
        HarnessConfig.model_validate(payload)


def test_harness_config_rejects_empty_watchtower_command(sample_harness_config):
    payload = sample_harness_config.model_dump()
    payload["watchtower"]["command"] = []

    with pytest.raises(ValidationError):
        HarnessConfig.model_validate(payload)


def test_load_config_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config(Path("missing.yaml"))
