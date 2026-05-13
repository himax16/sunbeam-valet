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

    assert config.mattermost is not None
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


def test_load_config_can_skip_mattermost_for_stdout(tmp_path):
    config_path = tmp_path / "harness.yaml"
    config_path.write_text(
        """
agents:
  - name: triage
    system_prompt: Prompt
    model: test
judge:
  name: judge
  system_prompt: Judge prompt
  model: test
mattermost:
  server_url: "${MATTERMOST_URL}"
  bot_token: "${MATTERMOST_BOT_TOKEN}"
  channel_id: "${MATTERMOST_CHANNEL_ID}"
watchtower:
  command: ["watchtower"]
""",
        encoding="utf-8",
    )

    config = load_config(config_path, require_mattermost=False)

    assert config.mattermost is None


def test_load_config_reads_system_prompt_files_relative_to_config(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent.md").write_text("Agent prompt\n", encoding="utf-8")
    (prompts_dir / "judge.md").write_text("Judge prompt\n", encoding="utf-8")

    config_path = tmp_path / "config" / "harness.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        """
agents:
  - name: triage
    system_prompt_file: ../prompts/agent.md
    model: test
judge:
  name: judge
  system_prompt_file: ../prompts/judge.md
  model: test
watchtower:
  command: ["watchtower"]
""",
        encoding="utf-8",
    )

    config = load_config(config_path, require_mattermost=False)

    assert config.agents[0].system_prompt == "Agent prompt\n"
    assert config.judge.system_prompt == "Judge prompt\n"


def test_load_config_rejects_mixed_inline_and_file_prompt(tmp_path):
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Prompt\n", encoding="utf-8")

    config_path = tmp_path / "harness.yaml"
    config_path.write_text(
        """
agents:
  - name: triage
    system_prompt: Inline prompt
    system_prompt_file: prompt.md
    model: test
judge:
  name: judge
  system_prompt: Judge prompt
  model: test
watchtower:
  command: ["watchtower"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="both system_prompt and system_prompt_file"):
        load_config(config_path, require_mattermost=False)


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
