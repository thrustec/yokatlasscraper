"""RAW insert and public analytics read API; bot administration stays unchanged."""
import secrets
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend import db
from backend.tuik_admin import router as tuik_admin_router


Name = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=63)]

app = FastAPI(
    title="YÖK Atlas — Veri API",
    version="1.0.0",
    description=(
        "POST /api/db/write yalnız RAW'a tek satır ekler ve X-API-Key ister. "
        "GET /api/db/read yalnız analytics'i okur ve herkese açıktır. "
        "Dönüşüm ve yayınlama ETL'nin sorumluluğundadır."
    ),
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

app.mount(
    "/admin/tuik/assets",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "frontend" / "tuik" / "assets"),
    name="tuik-admin-assets",
)
app.include_router(tuik_admin_router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    if request.url.path not in {"/api/db/read", "/api/db/write"}:
        return await request_validation_exception_handler(request, error)
    return JSONResponse(status_code=422, content={"detail": [
        {key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()
    ]})


class WriteRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True,
        json_schema_extra={"examples": [{"table": "ingestion_runs", "data": {
            "source_system": "yokatlas", "scraper_version": "raw-api-bots-v1",
        }}]},
    )
    table: Name
    data: dict[str, Any]


class WriteResponse(BaseModel):
    table: str
    key: dict[str, Any]


class ReadResponse(BaseModel):
    table: str
    data: list[dict[str, Any]]
    limit: int
    offset: int


write_key = APIKeyHeader(name="X-API-Key", scheme_name="RawWriteKey", auto_error=False)


def require_write_key(key: Annotated[str | None, Depends(write_key)]) -> None:
    expected = db.CONFIG.get("DB_WRITE_API_KEY")
    if not expected or expected.startswith("REPLACE_"):
        raise HTTPException(status_code=503, detail="DB_WRITE_API_KEY yapılandırılmamış.")
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Geçerli X-API-Key gerekli.")


async def exact_write_body(request: Request, body: WriteRequest) -> WriteRequest:
    # Keep decimal JSON tokens exact before checking PostgreSQL numeric precision.
    try:
        return WriteRequest.model_validate(db.parse_object(await request.body()))
    except ValidationError:
        raise HTTPException(status_code=422, detail="Geçerli table ve data objesi gerekli.") from None


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/status", tags=["Bağlantı"], summary="API ve veritabanı bağlantısı")
def health() -> dict[str, str]:
    with db.connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}


@app.post(
    "/api/db/write", status_code=201, tags=["Veri"],
    dependencies=[Depends(require_write_key)],
    summary="RAW tablosuna tek satır ekle",
    responses={code: {"description": description} for code, description in {
        401: "Geçersiz API anahtarı", 404: "Tablo yok veya erişilemiyor",
        409: "UNIQUE/FK çakışması", 422: "Doğrulama hatası", 503: "Veritabanı erişilemiyor",
    }.items()},
)
def write(body: Annotated[WriteRequest, Depends(exact_write_body)]) -> WriteResponse:
    return WriteResponse(table=body.table, key=db.insert_row(body.table, body.data))


@app.get(
    "/api/db/read", tags=["Veri"], summary="Analytics tablosu veya görünümünü oku",
    responses={404: {"description": "Tablo yok veya erişilemiyor"},
               503: {"description": "Veritabanı erişilemiyor"}},
)
def read(
    table: Annotated[Name, Query()],
    order_by: Annotated[list[Name], Query(min_length=1, description="Birden çok kolon için tekrarlayın")],
    filters: Annotated[str, Query(description='JSON obje; ör. {"yil":2026}')] = "{}",
    search_column: Annotated[Name | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    direction: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
) -> ReadResponse:
    if (search_column is None) != (q is None):
        raise HTTPException(status_code=422, detail="search_column ve q birlikte verilmeli.")
    rows = db.read_rows(table, db.parse_object(filters), order_by, direction,
                        search_column, q, limit, offset)
    return ReadResponse(table=table, data=jsonable_encoder(rows), limit=limit, offset=offset)
