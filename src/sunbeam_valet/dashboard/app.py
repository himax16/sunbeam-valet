import asyncio
import contextlib
import logging
from pathlib import Path
from typing import get_args

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from sunbeam_valet.dashboard import db as dashboard_db
from sunbeam_valet.dashboard import judge as dashboard_judge
from sunbeam_valet.dashboard import settings as dashboard_settings
from sunbeam_valet.dashboard import watchtower as dashboard_watchtower
from sunbeam_valet.dashboard.models import Bug, BugSource
from sunbeam_valet.dashboard.store import get_store

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

_VALID_SOURCES = set(get_args(BugSource))

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.autoescape = True


async def index(request: Request) -> HTMLResponse:
    store = get_store()
    bugs = store.list_all()
    settings = dashboard_settings.load_settings()
    last_sync = dashboard_db.get_last_sync()
    bug_count = len(bugs)
    return templates.TemplateResponse(
        request,
        "index.html.j2",
        {
            "bugs": bugs,
            "settings": settings,
            "last_sync": last_sync,
            "bug_count": bug_count,
        },
    )


async def bug_detail(request: Request) -> HTMLResponse:
    store = get_store()
    bug = store.get(request.path_params["id"])
    if bug is None:
        return HTMLResponse("Bug not found", status_code=404)
    judgements = dashboard_db.get_judgements(bug.id)
    return templates.TemplateResponse(
        request, "bug_detail.html.j2", {"bug": bug, "judgements": judgements}
    )


async def bug_triage(request: Request) -> Response:
    store = get_store()
    bug = store.get(request.path_params["id"])
    if bug is None:
        return HTMLResponse("Bug not found", status_code=404)

    bug.status = "triaging"
    store.update(bug)
    await asyncio.sleep(0.5)

    bug.classification = "bug"
    bug.priority = "medium"
    bug.action = "next release"
    bug.rationale = "Auto-triaged: moderate impact, standard handling path."
    bug.status = "triaged"
    store.update(bug)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "bug_row.html.j2", {"bug": bug})
    return RedirectResponse(url=f"/bug/{bug.id}", status_code=303)


async def bug_judge(request: Request) -> Response:
    store = get_store()
    bug = store.get(request.path_params["id"])
    if bug is None:
        return HTMLResponse("Bug not found", status_code=404)

    result = await dashboard_judge.run_judge(
        bug_id=bug.id,
        bug_title=bug.title,
        bug_description=bug.description,
        bug_source=str(bug.source),
        bug_status=bug.status,
    )

    if result.get("success"):
        verdict = result["verdict"]
    else:
        result = await dashboard_judge.demo_judge(
            bug_id=bug.id,
            bug_title=bug.title,
            bug_description=bug.description,
            bug_source=str(bug.source),
        )
        verdict = result["verdict"]

    priority_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    bug.priority = priority_map.get(verdict, "medium")
    bug.classification = "bug"
    bug.action = f"judged: {verdict}"
    bug.rationale = result.get("summary", "")
    bug.status = "accepted"
    store.update(bug)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "bug_row.html.j2", {"bug": bug})
    return RedirectResponse(url=f"/bug/{bug.id}", status_code=303)


async def bug_add(request: Request) -> Response:
    form = await request.form()
    title = str(form.get("title", "")).strip()
    description = str(form.get("description", "")).strip()
    source = str(form.get("source", "manual")).strip()
    source_val: BugSource = source if source in _VALID_SOURCES else "manual"  # type: ignore[assignment]

    if not title:
        return RedirectResponse(url="/", status_code=303)

    store = get_store()
    bug = Bug(title=title, description=description, source=source_val)
    store.add(bug)

    return RedirectResponse(url="/", status_code=303)


async def page_config(request: Request) -> HTMLResponse:
    settings = dashboard_settings.load_settings()
    return templates.TemplateResponse(request, "config.html.j2", {"settings": settings})


async def api_settings_save(request: Request) -> Response:
    form = await request.form()
    settings = dashboard_settings.load_settings()

    settings["watchtower_server_address"] = str(
        form.get("watchtower_server_address", settings["watchtower_server_address"])
    ).strip()
    settings["watchtower_server_host"] = str(
        form.get("watchtower_server_host", settings["watchtower_server_host"])
    ).strip()
    with contextlib.suppress(ValueError, TypeError):
        settings["watchtower_server_port"] = int(
            form.get("watchtower_server_port", settings["watchtower_server_port"])
        )
    settings["watchtower_token"] = str(
        form.get("watchtower_token", settings["watchtower_token"])
    ).strip()
    settings["watchtower_use_daemon"] = form.get("watchtower_use_daemon") == "on"
    settings["watchtower_config_path"] = str(
        form.get("watchtower_config_path", settings["watchtower_config_path"])
    ).strip()

    dashboard_settings.save_settings(settings)

    return RedirectResponse(url="/config", status_code=303)


async def api_sync(request: Request) -> JSONResponse:
    settings = dashboard_settings.load_settings()

    form = await request.form()
    projects_raw = str(form.get("projects", "")).strip()
    projects = [p.strip() for p in projects_raw.split(",") if p.strip()] if projects_raw else None

    result = await dashboard_watchtower.sync_bugs_from_watchtower(settings, projects)

    store = get_store()
    store.load_from_db()

    return JSONResponse(result)


async def api_sync_status(request: Request) -> JSONResponse:
    last = dashboard_db.get_last_sync()
    count = dashboard_db.count_bugs()
    logs = dashboard_db.get_sync_logs(limit=10)
    return JSONResponse(
        {
            "last_sync": last,
            "bug_count": count,
            "sync_logs": logs,
        }
    )


routes = [
    Route("/", index, methods=["GET"]),
    Route("/bug/{id}", bug_detail, methods=["GET"]),
    Route("/bug/{id}/triage", bug_triage, methods=["POST"]),
    Route("/bug/{id}/judge", bug_judge, methods=["POST"]),
    Route("/bug/add", bug_add, methods=["POST"]),
    Route("/config", page_config, methods=["GET"]),
    Route("/config/save", api_settings_save, methods=["POST"]),
    Route("/api/sync", api_sync, methods=["POST"]),
    Route("/api/sync/status", api_sync_status, methods=["GET"]),
]

app = Starlette(routes=routes)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def serve(host: str = "127.0.0.1", port: int = 8473) -> None:
    import uvicorn

    dashboard_db.init_db()
    get_store().load_from_db()
    uvicorn.run(app, host=host, port=port)
