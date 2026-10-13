"""Small PostgreSQL API demo with public reads and authenticated demo CRUD."""
import secrets
from pathlib import Path
from typing import Annotated, Literal

import psycopg
from dotenv import dotenv_values
from fastapi import Depends, FastAPI, HTTPException, Path as ApiPath, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyHeader
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


CONFIG = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
DEMO_CONFIG = dotenv_values(Path(__file__).resolve().parents[1] / ".env.demo")
UniversityId = Annotated[int, ApiPath(gt=0, le=9223372036854775807)]
Score = Literal["SAY", "EA", "SÖZ", "DİL", "TYT"]
Limit = Annotated[int, Query(ge=1, le=100, description="En fazla 100 kayıt")]
Offset = Annotated[int, Query(ge=0, description="Atlanacak kayıt sayısı")]
Year = Annotated[int | None, Query(ge=2000, le=2100)]

app = FastAPI(
    title="YÖK Atlas — Basit API Demosu",
    version="0.3.0",
    description=(
        "Docker PostgreSQL → mevcut API görünümleri → JSON. "
        "Okuma uçları giriş gerektirmez. Üniversite demo kayıtlarını ekleme, güncelleme "
        "ve silme için Authorize alanına X-API-Key girin. "
        "Yerel örnek veri tam veri setini temsil etmez; "
        "yıl alanı kaynaktan geldiği haliyle gösterilir."
    ),
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)


class University(BaseModel):
    universite_id: int
    universite_adi: str


class UniversityName(BaseModel):
    model_config = ConfigDict(extra="forbid")
    universite_adi: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] = Field(examples=["DEMO ÜNİVERSİTESİ — Güncellendi"])


class UniversityCreate(UniversityName):
    universite_id: int = Field(gt=0, le=9223372036854775807, examples=[900000001])


class Program(BaseModel):
    kilavuz_kodu: int
    yil: int
    puan_turu: str
    birim_adi: str
    universite_id: int
    universite_adi: str
    il_adi: str | None
    min_puan: float | None
    basari_sirasi: int | None
    kontenjan: int | None


class NetResult(BaseModel):
    kilavuz_kodu: int
    yil: int
    puan_turu: str
    taban_puan: float | None
    obp: float | None
    tyt_trk_net: float | None
    tyt_sos_net: float | None
    tyt_mat_net: float | None
    tyt_fen_net: float | None


def query(statement: str, params: dict | None = None) -> list[dict]:
    """Each short request uses the existing SELECT-only role."""
    try:
        with psycopg.connect(
            host="127.0.0.1",
            port=int(CONFIG.get("POSTGRES_PORT") or 5433),
            dbname="yokatlas_intelligence",
            user="atlas_api",
            password=CONFIG.get("ATLAS_API_PASSWORD"),
            connect_timeout=3,
            options="-c default_transaction_read_only=on -c statement_timeout=5000",
            row_factory=dict_row,
        ) as conn:
            return conn.execute(statement, params).fetchall()
    except psycopg.Error:
        raise HTTPException(
            status_code=503, detail="Veritabanına erişilemiyor. Docker PostgreSQL'i kontrol edin."
        ) from None


write_key = APIKeyHeader(name="X-API-Key", scheme_name="DemoWriteKey", auto_error=False)


def require_write_key(key: Annotated[str | None, Depends(write_key)]) -> None:
    expected = DEMO_CONFIG.get("DEMO_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Demo yazma kurulumu yapılmamış.")
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Geçerli X-API-Key gerekli.")


def write_query(statement: str, params: dict) -> list[dict]:
    """Commit one operation; PostgreSQL limits this role to manual demo rows."""
    try:
        with psycopg.connect(
            host="127.0.0.1", port=int(CONFIG.get("POSTGRES_PORT") or 5433),
            dbname="yokatlas_intelligence", user="atlas_demo_writer",
            password=DEMO_CONFIG.get("ATLAS_DEMO_WRITE_PASSWORD"),
            connect_timeout=3, options="-c statement_timeout=5000 -c lock_timeout=3000",
            row_factory=dict_row,
        ) as conn:
            return conn.execute(statement, params).fetchall()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Bu üniversite ID'si zaten mevcut.") from None
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status_code=409, detail="Programların kullandığı üniversite silinemez.") from None
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Veritabanı yazma işlemi tamamlanamadı.") from None


def demo_row_or_error(rows: list[dict], university_id: int) -> dict:
    if rows:
        return rows[0]
    existing = query(
        "SELECT universite_id FROM api.universities WHERE universite_id = %(id)s",
        {"id": university_id},
    )
    if existing:
        raise HTTPException(status_code=409, detail="YÖK Atlas kaynak kaydı korunuyor. Demo kaydı kullanın.")
    raise HTTPException(status_code=404, detail="Üniversite bulunamadı.")


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/docs")


@app.get("/status", tags=["1. Bağlantı"], summary="API ve veritabanı bağlantısı")
def health() -> dict[str, str]:
    query("SELECT 1 AS ok")
    return {"status": "ok", "database": "connected"}


@app.get("/api/veri-kapsami", tags=["1. Bağlantı"], summary="Yereldeki kayıt sayıları")
def coverage() -> dict[str, int]:
    return {
        row["entity"]: row["row_count"]
        for row in query("SELECT entity, row_count FROM api.data_coverage ORDER BY entity")
    }


@app.get("/api/universiteler", tags=["2. Üniversiteler"], summary="Üniversite listele / ara")
def universities(
    q: Annotated[str | None, Query(max_length=100, description="Üniversite adı")] = None,
    limit: Limit = 10,
    offset: Offset = 0,
) -> list[University]:
    return query(
        """SELECT universite_id, universite_adi FROM api.universities
           WHERE (%(q)s::text IS NULL OR universite_adi ILIKE %(q)s)
           ORDER BY universite_id LIMIT %(limit)s OFFSET %(offset)s""",
        {"q": f"%{q}%" if q else None, "limit": limit, "offset": offset},
    )


@app.get("/api/universiteler/{universite_id}", tags=["2. Üniversiteler"], summary="Tek üniversiteyi oku")
def university_detail(universite_id: UniversityId) -> University:
    rows = query(
        "SELECT universite_id, universite_adi FROM api.universities WHERE universite_id = %(id)s",
        {"id": universite_id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Üniversite bulunamadı.")
    return rows[0]


@app.post("/api/universiteler", status_code=201, tags=["2. Üniversiteler"],
          summary="Demo üniversitesi ekle", dependencies=[Depends(require_write_key)])
def create_university(body: UniversityCreate) -> University:
    return write_query(
        """INSERT INTO api.demo_universities (universite_id, universite_adi)
           VALUES (%(universite_id)s, %(universite_adi)s)
           RETURNING universite_id, universite_adi""",
        body.model_dump(),
    )[0]


@app.put("/api/universiteler/{universite_id}", tags=["2. Üniversiteler"],
         summary="Demo üniversitesinin adını güncelle", dependencies=[Depends(require_write_key)])
def update_university(universite_id: UniversityId, body: UniversityName) -> University:
    rows = write_query(
        """UPDATE api.demo_universities SET universite_adi = %(name)s, updated_at = now()
           WHERE universite_id = %(id)s RETURNING universite_id, universite_adi""",
        {"id": universite_id, "name": body.universite_adi},
    )
    return demo_row_or_error(rows, universite_id)


@app.delete("/api/universiteler/{universite_id}", status_code=204, tags=["2. Üniversiteler"],
            summary="Demo üniversitesini sil", dependencies=[Depends(require_write_key)])
def delete_university(universite_id: UniversityId) -> Response:
    rows = write_query(
        """DELETE FROM api.demo_universities WHERE universite_id = %(id)s
           RETURNING universite_id, universite_adi""",
        {"id": universite_id},
    )
    demo_row_or_error(rows, universite_id)
    return Response(status_code=204)


PROGRAM_COLUMNS = """kilavuz_kodu, yil, puan_turu, birim_adi, universite_id,
    universite_adi, il_adi, min_puan, basari_sirasi, kontenjan"""


@app.get("/api/programlar", tags=["3. Programlar"], summary="Programları filtrele")
def programs(
    q: Annotated[str | None, Query(max_length=100, description="Program adı")] = None,
    yil: Year = None,
    puan_turu: Score | None = None,
    universite_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Limit = 10,
    offset: Offset = 0,
) -> list[Program]:
    return query(
        f"""SELECT {PROGRAM_COLUMNS} FROM api.program_catalog
            WHERE (%(q)s::text IS NULL OR birim_adi ILIKE %(q)s)
              AND (%(yil)s::int IS NULL OR yil = %(yil)s)
              AND (%(puan_turu)s::text IS NULL OR puan_turu = %(puan_turu)s)
              AND (%(universite_id)s::bigint IS NULL OR universite_id = %(universite_id)s)
            ORDER BY yil DESC, kilavuz_kodu LIMIT %(limit)s OFFSET %(offset)s""",
        {"q": f"%{q}%" if q else None, "yil": yil, "puan_turu": puan_turu,
         "universite_id": universite_id, "limit": limit, "offset": offset},
    )


@app.get("/api/programlar/{kilavuz_kodu}", tags=["3. Programlar"], summary="Tek programın bilgileri")
def program_detail(
    kilavuz_kodu: Annotated[int, ApiPath(gt=0)],
    yil: Year = None,
) -> Program:
    rows = query(
        f"""SELECT {PROGRAM_COLUMNS} FROM api.program_catalog
            WHERE kilavuz_kodu = %(code)s AND (%(yil)s::int IS NULL OR yil = %(yil)s)
            ORDER BY yil DESC LIMIT 1""",
        {"code": kilavuz_kodu, "yil": yil},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Bu program yerel veri setinde bulunamadı.")
    return rows[0]


@app.get("/api/net-sonuclari", tags=["4. Netler"], summary="Yıl / puan türüne göre net sonuçları")
def net_results(
    yil: Year = None,
    puan_turu: Score | None = None,
    kilavuz_kodu: Annotated[int | None, Query(gt=0)] = None,
    limit: Limit = 10,
    offset: Offset = 0,
) -> list[NetResult]:
    return query(
        """SELECT kilavuz_kodu, yil, puan_turu, taban_puan, obp,
                  tyt_trk_net, tyt_sos_net, tyt_mat_net, tyt_fen_net
           FROM api.net_results
           WHERE (%(yil)s::int IS NULL OR yil = %(yil)s)
             AND (%(puan_turu)s::text IS NULL OR puan_turu = %(puan_turu)s)
             AND (%(code)s::bigint IS NULL OR kilavuz_kodu = %(code)s)
           ORDER BY yil DESC, kilavuz_kodu, puan_turu LIMIT %(limit)s OFFSET %(offset)s""",
        {"yil": yil, "puan_turu": puan_turu, "code": kilavuz_kodu,
         "limit": limit, "offset": offset},
    )
