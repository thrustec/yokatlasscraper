"""Short, role-specific transactions and live PostgreSQL column validation."""
import json
import logging
import os
import re
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from fastapi import HTTPException
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Json, Jsonb


CONFIG = {**dotenv_values(Path(__file__).resolve().parents[1] / ".env"), **os.environ}
LOG = logging.getLogger(__name__)
TEXT_TYPES = {"text", "varchar", "bpchar"}
INTEGER_BITS = {"int2": 16, "int4": 32, "int8": 64}
SUPPORTED_TYPES = TEXT_TYPES | INTEGER_BITS.keys() | {
    "numeric", "float4", "float8", "bool", "date", "timestamp", "timestamptz",
    "time", "timetz", "json", "jsonb",
}


def invalid(message: str):
    raise HTTPException(status_code=422, detail=message)


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def parse_object(value: str | bytes) -> dict:
    try:
        result = json.loads(value, parse_float=Decimal, parse_constant=reject_constant)
    except (ValueError, UnicodeDecodeError, RecursionError, InvalidOperation):
        invalid("Geçerli bir JSON obje gerekli.")
    if not isinstance(result, dict):
        invalid("Geçerli bir JSON obje gerekli.")
    return result


def json_text(value) -> str:
    """Preserve JSON numbers in JSON/JSONB too, without converting decimals to strings."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            invalid("JSON sayıları sonlu olmalı.")
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + ":" + json_text(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(json_text(item) for item in value) + "]"
    return json.dumps(value, allow_nan=False)


@contextmanager
def connection(*, write: bool = False):
    role = "atlas_raw_writer" if write else "atlas_analytics_reader"
    password = CONFIG.get("ATLAS_RAW_WRITER_PASSWORD" if write else "ATLAS_ANALYTICS_READER_PASSWORD")
    if not password or password.startswith("REPLACE_"):
        raise HTTPException(status_code=503, detail="Veri API veritabanı yapılandırması eksik.")
    try:
        with psycopg.connect(
            host=CONFIG.get("PGHOST") or "127.0.0.1",
            port=int(CONFIG.get("PGPORT") or CONFIG.get("POSTGRES_PORT") or 5433),
            dbname=CONFIG.get("PGDATABASE") or "yokatlas_intelligence",
            user=role, password=password, connect_timeout=3,
            options=("-c statement_timeout=5000 -c lock_timeout=3000 -c search_path=pg_catalog"
                     + ("" if write else " -c default_transaction_read_only=on")),
            row_factory=dict_row,
        ) as conn:
            yield conn
    except (psycopg.errors.UniqueViolation, psycopg.errors.ForeignKeyViolation):
        raise HTTPException(status_code=409, detail="Kayıt benzersizlik veya ilişki kısıtına uymuyor.") from None
    except (psycopg.DataError, psycopg.errors.CheckViolation, psycopg.errors.NotNullViolation):
        invalid("Kayıt tablonun veri tipi veya kısıtlarına uymuyor.")
    except (psycopg.errors.InsufficientPrivilege, psycopg.errors.UndefinedTable):
        raise HTTPException(status_code=404, detail="Tablo yok veya erişilemiyor.") from None
    except psycopg.Error as error:
        LOG.warning("Data API database operation failed: %s (%s)", type(error).__name__, error.sqlstate)
        raise HTTPException(status_code=503, detail="Veritabanı işlemi tamamlanamadı.") from None


def columns(conn, schema: str, table: str, *, write: bool = False) -> dict[str, dict]:
    relation = conn.execute(
        """SELECT c.oid FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=%s AND c.relname=%s AND c.relkind=ANY(%s)
             AND pg_catalog.has_schema_privilege(n.oid, 'USAGE')
             AND pg_catalog.has_table_privilege(c.oid, %s)""",
        (schema, table, ["r", "p"] if write else ["r", "p", "v", "m"],
         "INSERT" if write else "SELECT"),
    ).fetchone()
    if not relation:
        raise HTTPException(status_code=404, detail="Tablo yok veya erişilemiyor.")
    rows = conn.execute(
        """SELECT a.attname AS name, t.typname AS type,
                  t.typnamespace='pg_catalog'::regnamespace AS builtin,
                  pg_catalog.format_type(a.atttypid,a.atttypmod) AS sql_type,
                  a.atttypmod AS modifier, a.attnotnull AS required,
                  a.atthasdef AS has_default,
                  a.attidentity<>'' OR a.attgenerated<>'' AS generated,
                  EXISTS (SELECT 1 FROM pg_catalog.pg_index i
                          WHERE i.indrelid=a.attrelid AND i.indisprimary
                            AND a.attnum=ANY((i.indkey::smallint[])[0:i.indnkeyatts-1])) AS primary_key
           FROM pg_catalog.pg_attribute a
           JOIN pg_catalog.pg_type t ON t.oid=a.atttypid
           WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped
           ORDER BY a.attnum""",
        (relation["oid"],),
    ).fetchall()
    return {row["name"]: row for row in rows}


def validate_value(column: dict, value):
    name, kind = column["name"], column["type"]
    if not column["builtin"] or kind not in SUPPORTED_TYPES:
        invalid(f"{name}: desteklenmeyen kolon tipi ({column['sql_type']}).")
    if value is None:
        if column["required"]:
            invalid(f"{name}: null olamaz.")
        return None
    if kind in INTEGER_BITS:
        bound = 2 ** (INTEGER_BITS[kind] - 1)
        if type(value) is not int or not -bound <= value < bound:
            invalid(f"{name}: {kind} aralığında JSON integer gerekli.")
    elif kind in {"numeric", "float4", "float8"}:
        if type(value) not in (int, float, Decimal):
            invalid(f"{name}: JSON sayı gerekli.")
        number = Decimal(str(value))
        if not number.is_finite():
            invalid(f"{name}: sonlu sayı gerekli.")
        if kind == "numeric":
            constraint = re.fullmatch(r"numeric\((\d+),(-?\d+)\)", column["sql_type"])
            if constraint:
                precision, scale = map(int, constraint.groups())
                digits = "".join(map(str, number.as_tuple().digits))
                trailing_zeros = len(digits) - len(digits.rstrip("0"))
                if number and (number.as_tuple().exponent + trailing_zeros < -scale
                               or number.copy_abs() >= Decimal(1).scaleb(precision - scale)):
                    invalid(f"{name}: {column['sql_type']} hassasiyetine uymuyor.")
            return number
        maximum = Decimal("3.4028234663852886e38" if kind == "float4" else "1.7976931348623157e308")
        if number.copy_abs() > maximum:
            invalid(f"{name}: {kind} aralığı dışında.")
        converted = float(number)
        if number and (converted == 0 or (kind == "float4" and number.copy_abs() < Decimal("1.401298464324817e-45"))):
            invalid(f"{name}: {kind} aralığı dışında.")
        return converted
    elif kind in TEXT_TYPES:
        if type(value) is not str or "\x00" in value:
            invalid(f"{name}: geçerli JSON metin gerekli.")
        try:
            value.encode("utf-8")
        except UnicodeError:
            invalid(f"{name}: geçerli UTF-8 metin gerekli.")
        if column["modifier"] >= 4 and len(value) > column["modifier"] - 4:
            invalid(f"{name}: metin kolon uzunluğunu aşıyor.")
    elif kind == "bool":
        if type(value) is not bool:
            invalid(f"{name}: JSON boolean gerekli.")
    elif kind in {"date", "timestamp", "timestamptz", "time", "timetz"}:
        if type(value) is not str:
            invalid(f"{name}: ISO 8601 metin gerekli.")
        try:
            if kind == "date":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError
                return date.fromisoformat(value)
            if kind in {"timestamp", "timestamptz"}:
                if "T" not in value:
                    raise ValueError
                converted = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                converted = time.fromisoformat(value.replace("Z", "+00:00"))
            if (converted.tzinfo is not None) != (kind in {"timestamptz", "timetz"}):
                raise ValueError
            fraction = re.search(r"\.(\d+)", value)
            precision = column["modifier"] if column["modifier"] >= 0 else 6
            if fraction and len(fraction[1].rstrip("0")) > precision:
                raise ValueError
            return converted
        except ValueError:
            invalid(f"{name}: {column['sql_type']} için geçerli ISO 8601 değer gerekli.")
    elif kind in {"json", "jsonb"}:
        return (Jsonb if kind == "jsonb" else Json)(value, dumps=json_text)
    return value


def insert_row(table: str, data: dict) -> dict:
    with connection(write=True) as conn:
        metadata = columns(conn, "raw", table, write=True)
        unknown = data.keys() - metadata.keys()
        if unknown:
            invalid("Bilinmeyen kolon: " + ", ".join(sorted(unknown)))
        for name, column in metadata.items():
            if column["generated"]:
                if name in data:
                    invalid(f"{name}: sunucu tarafından üretilir.")
            elif column["required"] and not column["has_default"] and name not in data:
                invalid(f"{name}: zorunlu kolon eksik.")
        values = [validate_value(metadata[name], value) for name, value in data.items()]
        key_names = [name for name, column in metadata.items() if column["primary_key"]]
        statement = sql.SQL("INSERT INTO {} ").format(sql.Identifier("raw", table))
        if data:
            statement += sql.SQL("({}) VALUES ({})").format(
                sql.SQL(", ").join(map(sql.Identifier, data)),
                sql.SQL(", ").join(sql.Placeholder() for _ in data),
            )
        else:
            statement += sql.SQL("DEFAULT VALUES")
        if key_names:
            statement += sql.SQL(" RETURNING {} ").format(sql.SQL(", ").join(map(sql.Identifier, key_names)))
        cursor = conn.execute(statement, values)
        result = cursor.fetchone() if key_names else {}
    return result


def read_rows(table, filters, order_by, direction, search_column, q, limit, offset):
    with connection() as conn:
        metadata = columns(conn, "analytics", table)
        names = set(filters) | set(order_by) | ({search_column} if search_column is not None else set())
        if names - metadata.keys():
            invalid("Bilinmeyen sorgu kolonu.")
        conditions, values = [], []
        for name, value in filters.items():
            column = sql.Identifier(name)
            if value is None:
                conditions.append(sql.SQL("{} IS NULL").format(column))
            else:
                values.append(validate_value(metadata[name], value))
                if metadata[name]["type"] == "json":
                    conditions.append(sql.SQL("{}::jsonb = %s::jsonb").format(column))
                else:
                    conditions.append(sql.SQL("{} = %s").format(column))
        if search_column is not None:
            if metadata[search_column]["type"] not in TEXT_TYPES or not metadata[search_column]["builtin"]:
                invalid("Arama kolonu metin tipinde olmalı.")
            conditions.append(sql.SQL("{} ILIKE %s ESCAPE E'\\\\'").format(sql.Identifier(search_column)))
            values.append("%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        ordering = []
        for name in order_by:
            column = metadata[name]
            if not column["builtin"] or column["type"] not in SUPPORTED_TYPES:
                invalid("Sıralama kolonunun tipi desteklenmiyor.")
            ordering.append(sql.SQL("{}{} {}").format(
                sql.Identifier(name), sql.SQL("::jsonb" if column["type"] == "json" else ""),
                sql.SQL("DESC" if direction == "desc" else "ASC"),
            ))
        statement = sql.SQL("SELECT * FROM {}").format(sql.Identifier("analytics", table))
        if conditions:
            statement += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
        statement += sql.SQL(" ORDER BY {} LIMIT %s OFFSET %s").format(sql.SQL(", ").join(ordering))
        return conn.execute(statement, [*values, limit, offset]).fetchall()
