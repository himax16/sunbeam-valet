import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _env_var_constructor(loader, node):
    value = loader.construct_scalar(node)
    matches = _ENV_VAR_PATTERN.findall(value)
    for var in matches:
        value = value.replace(f"${{{var}}}", os.environ.get(var, ""))
    return value


class AgentConfig(BaseModel):
    name: str
    system_prompt: str
    model: str


class JudgeConfig(BaseModel):
    name: str
    system_prompt: str
    model: str
    consensus_threshold: float = Field(ge=0.0, le=1.0, default=0.7)


class RoutingConfig(BaseModel):
    strategy: Literal["all_agents"] = "all_agents"


class Round2TriggerConfig(BaseModel):
    metric: str = "std_dev"
    threshold: float = Field(ge=0.0)


class MattermostConfig(BaseModel):
    server_url: str
    bot_token: str
    channel_id: str


class WatchtowerConfig(BaseModel):
    command: list[str] = Field(min_length=1)
    bug_filter: dict[str, list[str]] = Field(default_factory=dict)


class HarnessConfig(BaseModel):
    agents: list[AgentConfig] = Field(min_length=1)
    judge: JudgeConfig
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    round2_trigger: Round2TriggerConfig = Field(
        default_factory=lambda: Round2TriggerConfig(metric="std_dev", threshold=0.3)
    )
    max_rounds: int = Field(default=2)
    mattermost: MattermostConfig
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


def load_config(path: str | Path) -> HarnessConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    class EnvLoader(yaml.SafeLoader):
        pass

    EnvLoader.add_constructor("!env", _env_var_constructor)

    with open(path, encoding="utf-8") as f:
        raw = yaml.load(f, Loader=EnvLoader)

    processed = _substitute_env_vars(raw)
    return HarnessConfig.model_validate(processed)


def _substitute_env_vars(obj):
    if isinstance(obj, str):
        matches = _ENV_VAR_PATTERN.findall(obj)
        for var in matches:
            if var not in os.environ or os.environ[var] == "":
                raise ValueError(f"Environment variable {var} is required")
            obj = obj.replace(f"${{{var}}}", os.environ[var])
        return obj
    elif isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj
