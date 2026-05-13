import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")
type YamlValue = str | int | float | bool | None | list[YamlValue] | dict[str, YamlValue]


class EnvLoader(yaml.SafeLoader):
    pass


def _replace_required_env_vars(value: str) -> str:
    for var in _ENV_VAR_PATTERN.findall(value):
        if var not in os.environ or os.environ[var] == "":
            raise ValueError(f"Environment variable {var} is required")
        value = value.replace(f"${{{var}}}", os.environ[var])
    return value


def _env_var_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    value = loader.construct_scalar(node)
    return _replace_required_env_vars(value)


class AgentConfig(BaseModel):
    name: str
    system_prompt: str
    model: str


class JudgeConfig(BaseModel):
    name: str
    system_prompt: str
    model: str


class Round2TriggerConfig(BaseModel):
    metric: Literal["std_dev"] = "std_dev"
    threshold: float = Field(ge=0.0)


class MattermostConfig(BaseModel):
    mode: Literal["bot", "webhook"] = "bot"
    server_url: str | None = None
    bot_token: str | None = None
    channel_id: str | None = None
    webhook_url: str | None = None

    @model_validator(mode="after")
    def _validate_mode_fields(self) -> "MattermostConfig":
        if self.mode == "bot":
            missing = [
                field
                for field in ("server_url", "bot_token", "channel_id")
                if getattr(self, field) in {None, ""}
            ]
            if missing:
                raise ValueError("bot mode requires server_url, bot_token, and channel_id")
            if self.webhook_url:
                raise ValueError("bot mode cannot define webhook_url")
        elif self.mode == "webhook":
            if not self.webhook_url:
                raise ValueError("webhook mode requires webhook_url")
            bot_fields = [
                field
                for field in ("server_url", "bot_token", "channel_id")
                if getattr(self, field) not in {None, ""}
            ]
            if bot_fields:
                raise ValueError("webhook mode cannot define server_url, bot_token, or channel_id")
        return self


class WatchtowerBugFilter(BaseModel):
    status: list[str] = Field(default_factory=list)


class WatchtowerConfig(BaseModel):
    command: list[str] = Field(min_length=1)
    bug_filter: WatchtowerBugFilter = Field(default_factory=WatchtowerBugFilter)


class HarnessConfig(BaseModel):
    agents: list[AgentConfig] = Field(min_length=1)
    judge: JudgeConfig
    round2_trigger: Round2TriggerConfig = Field(
        default_factory=lambda: Round2TriggerConfig(metric="std_dev", threshold=0.3)
    )
    max_rounds: int = Field(default=2)
    mattermost: MattermostConfig | None = None
    watchtower: WatchtowerConfig

    @field_validator("max_rounds")
    @classmethod
    def _validate_max_rounds(cls, value: int) -> int:
        if value not in {1, 2}:
            raise ValueError("max_rounds must be 1 or 2")
        return value

    @model_validator(mode="after")
    def _validate_unique_agent_names(self) -> "HarnessConfig":
        names = [agent.name for agent in self.agents]
        if len(set(names)) != len(names):
            raise ValueError("agent names must be unique")
        return self


def load_config(path: str | Path, *, require_mattermost: bool = True) -> HarnessConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    EnvLoader.add_constructor("!env", _env_var_constructor)

    with open(path, encoding="utf-8") as f:
        raw = yaml.load(f, Loader=EnvLoader)

    if not require_mattermost and isinstance(raw, dict):
        raw = dict(raw)
        raw.pop("mattermost", None)

    processed = _substitute_env_vars(raw)
    _load_system_prompt_files(processed, base_dir=path.parent)
    config = HarnessConfig.model_validate(processed)
    if require_mattermost and config.mattermost is None:
        raise ValueError("Mattermost configuration is required for Mattermost output")
    return config


def _substitute_env_vars(obj: Any) -> YamlValue:
    if isinstance(obj, str):
        return _replace_required_env_vars(obj)
    elif isinstance(obj, dict):
        return {str(k): _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


def _load_system_prompt_files(obj: YamlValue, *, base_dir: Path) -> None:
    if not isinstance(obj, dict):
        return

    for section in _prompt_sections(obj):
        if not isinstance(section, dict):
            continue

        prompt_file = section.pop("system_prompt_file", None)
        has_inline_prompt = "system_prompt" in section
        if prompt_file is None:
            continue

        if has_inline_prompt:
            name = section.get("name", "unknown")
            raise ValueError(f"{name} cannot define both system_prompt and system_prompt_file")
        if not isinstance(prompt_file, str):
            raise ValueError("system_prompt_file must be a string path")

        prompt_path = Path(prompt_file)
        if not prompt_path.is_absolute():
            prompt_path = base_dir / prompt_path
        try:
            section["system_prompt"] = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}") from exc


def _prompt_sections(obj: dict[str, YamlValue]) -> list[YamlValue]:
    sections: list[YamlValue] = []
    agents = obj.get("agents", [])
    if isinstance(agents, list):
        sections.extend(agents)
    judge = obj.get("judge")
    if judge is not None:
        sections.append(judge)
    return sections
