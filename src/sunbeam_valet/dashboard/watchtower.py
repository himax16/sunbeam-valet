import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from sunbeam_valet.dashboard.db import finish_sync, replace_bugs, start_sync
from sunbeam_valet.dashboard.models import Bug

logger = logging.getLogger(__name__)

WATCHTOWER_BINARY = "watchtower"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "sunbeam-watchtower" / "config.yaml"
HEALTH_TIMEOUT = 10.0
HEALTH_POLL_INTERVAL = 0.5


async def check_watchtower_health(server_address: str, token: str = "") -> bool:
    url = f"{server_address}/api/v1/health"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            return resp.status_code == 200
    except Exception:
        return False


async def start_watchtower_if_needed(
    settings: dict[str, Any],
) -> tuple[bool, str, str]:
    """Start watchtower if needed. Returns (ok, message, effective_address)."""
    address = settings["watchtower_server_address"]
    token = settings.get("watchtower_token", "")

    is_healthy = await check_watchtower_health(address, token)
    if is_healthy:
        logger.info("Watchtower server at %s is already healthy", address)
        return True, "Watchtower server is already running.", address

    config_path = settings.get("watchtower_config_path", str(DEFAULT_CONFIG_PATH))

    if settings.get("watchtower_use_daemon", False):
        ok, msg, resolved = await _start_daemon(config_path, token)
        return ok, msg, resolved if ok else address
    else:
        host = settings.get("watchtower_server_host", "127.0.0.1")
        port = settings.get("watchtower_server_port", 8472)
        resolved = f"http://{host}:{port}"
        ok, msg = await _start_direct(host, port, config_path, token)
        return ok, msg, resolved


def _build_serve_args(host: str, port: int, config_path: str) -> list[str]:
    args = [WATCHTOWER_BINARY, "serve", "--listen", f"{host}:{port}"]
    if os.path.exists(config_path):
        args.extend(["--config", config_path])
    return args


async def _start_direct(
    host: str, port: int, config_path: str, token: str = ""
) -> tuple[bool, str]:
    cmd = _build_serve_args(host, port, config_path)
    logger.info("Starting watchtower serve: %s", " ".join(cmd))
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        return False, f"watchtower binary not found. Is {WATCHTOWER_BINARY} installed?"
    except Exception as e:
        return False, f"Failed to start watchtower: {e}"

    address = f"http://{host}:{port}"
    return await _wait_for_health(address, token)


def _build_daemon_args(config_path: str) -> list[str]:
    args = [WATCHTOWER_BINARY, "server", "start"]
    if os.path.exists(config_path):
        args.extend(["--config", config_path])
    return args


async def _start_daemon(config_path: str, token: str = "") -> tuple[bool, str, str]:
    """Start watchtower in daemon mode. Returns (ok, message, resolved_address)."""
    cmd = _build_daemon_args(config_path)
    logger.info("Starting watchtower daemon: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:200] if result.stderr else "unknown error"
            return False, f"watchtower server start failed (rc={result.returncode}): {stderr}", ""
    except FileNotFoundError:
        return (
            False,
            f"watchtower binary not found. Is {WATCHTOWER_BINARY} installed?",
            "",
        )
    except subprocess.TimeoutExpired:
        return False, "watchtower server start timed out", ""
    except Exception as e:
        return False, f"Failed to start watchtower daemon: {e}", ""

    metadata_path = _find_runtime_dir() / "watchtower.json"
    try:
        with open(metadata_path) as f:
            meta = json.load(f)
        address = meta.get("address", "")
        if address:
            ok, msg = await _wait_for_health(address, token)
            return ok, msg, address
    except Exception:
        pass

    return False, "Daemon started but could not determine server address.", ""


def _find_runtime_dir() -> Path:
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if xdg_runtime:
        return Path(xdg_runtime) / "sunbeam-watchtower"
    return Path.home() / ".cache" / "sunbeam-watchtower" / "run"


async def _wait_for_health(address: str, token: str = "") -> tuple[bool, str]:
    deadline = time.time() + HEALTH_TIMEOUT
    while time.time() < deadline:
        if await check_watchtower_health(address, token):
            return True, "Watchtower server started and healthy."
        await asyncio.sleep(HEALTH_POLL_INTERVAL)

    return False, (
        f"Watchtower server at {address} did not become healthy within {HEALTH_TIMEOUT}s."
    )


async def sync_bugs_from_watchtower(
    settings: dict[str, Any], projects: list[str] | None = None
) -> dict[str, Any]:
    token = settings.get("watchtower_token", "")

    log_id = start_sync()

    user_message = ""
    success = True
    total = 0

    try:
        server_ok, msg, address = await start_watchtower_if_needed(settings)
        user_message += msg + "\n"
        if not server_ok:
            user_message += "Sync aborted: server not available.\n"
            finish_sync(log_id, 0, "server not available")
            return {"success": False, "message": user_message, "count": 0, "log_id": log_id}

        sync_msg = await _trigger_server_sync(address, token, projects)
        user_message += sync_msg

        bugs = await _fetch_bugs(address, token)

        total = replace_bugs(bugs)
        user_message += f"Replaced local cache with {total} bugs from watchtower.\n"

        finish_sync(log_id, total)
    except Exception as exc:
        user_message += f"Sync failed: {exc}\n"
        finish_sync(log_id, 0, str(exc))
        success = False

    return {
        "success": success,
        "message": user_message,
        "count": total,
        "log_id": log_id,
    }


async def _trigger_server_sync(address: str, token: str, projects: list[str] | None) -> str:
    url = f"{address}/api/v1/cache/sync/bugs"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = {}
    if projects:
        body["projects"] = projects

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code in (200, 202, 204):
                data = resp.json() if resp.content else {}
                synced = data.get("synced", "?")
                return f"Server sync triggered: {synced} tasks synced.\n"
            else:
                text = resp.text[:200]
                return f"Server sync returned status {resp.status_code}: {text}\n"
    except Exception as exc:
        return f"Failed to trigger server sync: {exc}\n"


async def _fetch_bugs(address: str, token: str) -> list[Bug]:
    url = f"{address}/api/v1/bugs"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning("Bug API returned %d: %s", resp.status_code, resp.text[:200])
                return []

            data = resp.json()
            bugs_raw = data if isinstance(data, list) else data.get("bugs", [])
            bugs: list[Bug] = []
            for item in bugs_raw:
                if not isinstance(item, dict):
                    continue
                try:
                    bugs.append(_parse_bug(item))
                except Exception:
                    logger.warning("Skipping unparseable bug: %s", item.get("id", "?"))
            return bugs
    except Exception as exc:
        logger.warning("Bug API request failed: %s", exc)
    return []


def _parse_bug(raw: dict[str, Any]) -> Bug:
    return Bug(
        id=str(raw.get("id", "")),
        title=str(raw.get("title", "")),
        status=str(raw.get("status", "")),
        importance=str(raw.get("importance", "")),
        description=str(raw.get("description", "")),
        url=str(raw.get("url", "")),
        source=raw.get("source", "launchpad"),
    )
