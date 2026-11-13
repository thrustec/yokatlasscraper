"""Authenticated operator API for listing and manually starting bot runs."""
from __future__ import annotations

import secrets
from pathlib import Path
from typing import Annotated

from dotenv import dotenv_values
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path as ApiPath, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.tuik_jobs import BOT_ID, TuikError, create_run, get_run, list_datasets, list_runs, run_ingestion


ROOT = Path(__file__).resolve().parents[1]
CONFIG = dotenv_values(ROOT / ".env")
router = APIRouter()
ops_key_header = APIKeyHeader(name="X-API-Key", scheme_name="BotOpsKey", auto_error=False)
DataflowId = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9_]+$", min_length=1, max_length=100)]
DataflowVersion = Annotated[str, StringConstraints(pattern=r"^\d+(?:\.\d+){1,2}$", min_length=3, max_length=20)]
BotId = Annotated[str, ApiPath(pattern=r"^[a-z0-9-]+$")]
RunId = Annotated[int, ApiPath(gt=0)]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataflow_id: DataflowId
    version: DataflowVersion
    year: int = Field(ge=1900, le=2100)


def require_ops_key(key: Annotated[str | None, Depends(ops_key_header)]) -> None:
    expected = CONFIG.get("BOT_ADMIN_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Bot yönetimi için BOT_ADMIN_API_KEY sunucuda tanımlanmalı.")
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Geçerli X-API-Key gerekli.")


def require_tuik(bot_id: str) -> None:
    if bot_id != BOT_ID:
        raise HTTPException(status_code=404, detail="Bot bulunamadı.")


@router.get("/admin/tuik", include_in_schema=False)
def tuik_admin_redirect() -> RedirectResponse:
    return RedirectResponse("/admin/tuik/", status_code=307)


@router.get("/admin/tuik/", include_in_schema=False)
def tuik_admin_page() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "tuik" / "index.html")


@router.get("/ops/v1/bots", tags=["Bot yönetimi"], dependencies=[Depends(require_ops_key)])
def bots() -> list[dict]:
    return [
        {"bot_id": BOT_ID, "name": "TÜİK SDMX", "manual_runs": True,
         "scheduling": False,
         "status": "ready" if CONFIG.get("TUIK_API_KEY") else "needs_configuration"},
        {"bot_id": "yokatlas", "name": "YÖK Atlas", "manual_runs": False,
         "scheduling": False, "status": "cli_only"},
        {"bot_id": "sege", "name": "SEGE PDF", "manual_runs": False,
         "scheduling": False, "status": "cli_only", "command": "python -m scraper.panel_sege"},
        {"bot_id": "urap", "name": "URAP PDF", "manual_runs": False,
         "scheduling": False, "status": "cli_only", "command": "python -m scraper.panel_urap"},
    ]


@router.get("/ops/v1/bots/{bot_id}/datasets", tags=["Bot yönetimi"],
            dependencies=[Depends(require_ops_key)])
def datasets(bot_id: BotId) -> dict:
    require_tuik(bot_id)
    try:
        items = list_datasets()
    except TuikError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    groups: dict[str, dict] = {}
    for item in items:
        group = groups.setdefault(item["category_id"], {"id": item["category_id"],
                                                          "name": item["category"], "datasets": []})
        group["datasets"].append(item)
    return {"bot_id": bot_id, "categories": list(groups.values()), "dataset_count": len(items)}


@router.get("/ops/v1/bots/{bot_id}/runs", tags=["Bot yönetimi"],
            dependencies=[Depends(require_ops_key)])
def runs(bot_id: BotId, limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict:
    require_tuik(bot_id)
    try:
        return {"items": list_runs(limit)}
    except Exception:
        raise HTTPException(status_code=503, detail="Bot çalışma geçmişi okunamadı.") from None


@router.get("/ops/v1/bots/{bot_id}/runs/{run_id}", tags=["Bot yönetimi"],
            dependencies=[Depends(require_ops_key)])
def run_detail(bot_id: BotId, run_id: RunId) -> dict:
    require_tuik(bot_id)
    try:
        run = get_run(run_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Bot çalışma durumu okunamadı.") from None
    if not run:
        raise HTTPException(status_code=404, detail="Bot çalışması bulunamadı.")
    return run


@router.post("/ops/v1/bots/{bot_id}/runs", status_code=202, tags=["Bot yönetimi"],
             dependencies=[Depends(require_ops_key)])
def start_run(bot_id: BotId, body: RunRequest, background_tasks: BackgroundTasks) -> dict:
    require_tuik(bot_id)
    try:
        catalog = list_datasets()
        dataset = next((item for item in catalog if item["id"] == body.dataflow_id
                        and item["version"] == body.version), None)
        if not dataset:
            raise HTTPException(status_code=422, detail="Seçilen veri akışı TÜİK kataloğunda yok.")
        run_id = create_run(dataset, body.year)
    except TuikError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Bot çalışması başlatılamadı.") from None
    background_tasks.add_task(run_ingestion, run_id, dataset, body.year)
    return {"run_id": str(run_id), "bot_id": bot_id, "status": "queued"}
