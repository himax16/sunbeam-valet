import json
from pathlib import Path
from typing import Any

SETTINGS_PATH = Path.home() / ".config" / "sunbeam-valet" / "dashboard_settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "watchtower_server_address": "http://127.0.0.1:8472",
    "watchtower_token": "",
    "watchtower_use_daemon": False,
    "watchtower_server_port": 8472,
    "watchtower_server_host": "127.0.0.1",
    "watchtower_config_path": str(Path.home() / ".config" / "sunbeam-watchtower" / "config.yaml"),
}


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH) as f:
            saved = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_SETTINGS)
    merged = dict(DEFAULT_SETTINGS)
    merged.update(saved)
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    filtered = {k: settings[k] for k in DEFAULT_SETTINGS if k in settings}
    with open(SETTINGS_PATH, "w") as f:
        json.dump(filtered, f, indent=2)
