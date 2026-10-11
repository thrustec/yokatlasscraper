"""Collect public YÖK Atlas JSON responses into the existing archive layout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urljoin
import uuid

from scraper.common.archive import sha256_bytes, utc_now, write_bytes, write_json_atomic
from scraper.common.http_client import HttpClient, RetryPolicy


BASE_URL = "https://yokatlas.yok.gov.tr/"
LOOKUPS = (
    ("universities", "/api/tercih-kilavuz/universiteler"),
    ("program_groups", "/api/tercih-kilavuz/universite-programlar"),
    ("cities", "/api/tercih-kilavuz/universite-iller"),
)
SEARCHES = (
    ("programs", "/api/tercih-kilavuz/search"),
    ("net_results", "/api/netler/search"),
)
SCORE_TYPES = ("SAY", "EA", "SÖZ", "DİL", "TYT")


class CollectionError(RuntimeError):
    pass


class YokAtlasCollector:
    def __init__(
        self,
        *,
        output_dir: Path,
        delay_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        max_attempts: int = 5,
        max_requests: int = 5000,
        max_pages_per_score: int = 10000,
        page_size: int = 100,
        refresh: bool = False,
    ) -> None:
        if delay_seconds < 1.0:
            raise ValueError("delay_seconds must be at least 1 second")
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        if max_requests < 1 or max_pages_per_score < 1:
            raise ValueError("request and page limits must be positive")

        self.output_dir = output_dir
        self.data_dir = output_dir / "complete_data"
        self.refresh = refresh
        self.max_requests = max_requests
        self.max_pages_per_score = max_pages_per_score
        self.page_size = page_size
        self.request_count = 0
        self.client = HttpClient(
            minimum_interval_seconds=delay_seconds,
            timeout_seconds=timeout_seconds,
            retry_policy=RetryPolicy(max_attempts=max_attempts),
            user_agent="YOKAtlasIntelligence/0.1 (read-only research collector)",
        )
        self.manifest: dict[str, Any] = {
            "run_id": str(uuid.uuid4()),
            "source_system": "yokatlas",
            "started_at": utc_now(),
            "status": "running",
            "minimum_request_interval_seconds": delay_seconds,
            "responses": [],
            "failures": [],
            "coverage": [],
        }
        self.manifest_path = output_dir / "collection_runs" / f"{self.manifest['run_id']}.json"

    def _save_manifest(self) -> None:
        write_json_atomic(self.manifest_path, self.manifest)
        write_json_atomic(self.output_dir / "collection_manifest.json", self.manifest)

    def _load_or_fetch(
        self,
        *,
        endpoint: str,
        method: str,
        payload: dict[str, Any] | None,
        relative_path: str,
        entity: str,
        score_type: str | None = None,
        page_number: int | None = None,
    ) -> object:
        destination = self.data_dir / relative_path
        if destination.exists() and not self.refresh:
            try:
                raw_body = destination.read_bytes()
                data = json.loads(raw_body)
                self.manifest["responses"].append({
                    "entity": entity,
                    "endpoint": endpoint,
                    "method": method,
                    "request_payload": payload,
                    "score_type": score_type,
                    "page_number": page_number,
                    "path": f"complete_data/{relative_path}",
                    "sha256": sha256_bytes(raw_body),
                    "byte_count": len(raw_body),
                    "cached": True,
                })
                return data
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                # A damaged cache entry is replaced by a fresh source response.
                pass

        if self.client.requests_made >= self.max_requests:
            raise CollectionError(f"request limit reached ({self.max_requests})")

        url = urljoin(BASE_URL, endpoint.lstrip("/"))
        try:
            remaining_budget = self.max_requests - self.client.requests_made
            response = self.client.request(
                method,
                url,
                json_body=payload,
                max_attempts=min(self.client.retry_policy.max_attempts, remaining_budget),
            )
            receipt = write_bytes(self.data_dir, relative_path, response.content)
            event = {
                "entity": entity,
                "endpoint": endpoint,
                "method": method,
                "request_payload": payload,
                "score_type": score_type,
                "page_number": page_number,
                "http_status": response.status_code,
                "captured_at": receipt.captured_at,
                "sha256": receipt.sha256,
                "byte_count": receipt.byte_count,
                "path": f"complete_data/{receipt.path}",
                "attempts": getattr(response, "_codex_attempt_count", 1),
                "cached": False,
            }
            self.manifest["responses"].append(event)
            self._save_manifest()
            try:
                return json.loads(response.content)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CollectionError(f"{endpoint} returned malformed JSON; raw body was archived") from exc
        except Exception as exc:
            self.manifest["failures"].append({
                "entity": entity,
                "endpoint": endpoint,
                "score_type": score_type,
                "page_number": page_number,
                "error": f"{type(exc).__name__}: {exc}",
                "time": utc_now(),
            })
            self._save_manifest()
            raise

    def _collect_lookup(self, entity: str, endpoint: str) -> None:
        data = self._load_or_fetch(
            endpoint=endpoint,
            method="GET",
            payload=None,
            relative_path=f"{entity}/all.json",
            entity=entity,
        )
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise CollectionError(f"{entity}: expected a JSON array of objects")
        self.manifest["coverage"].append({"entity": entity, "records": len(data)})
        self._save_manifest()

    def _collect_search(self, entity: str, endpoint: str, score_type: str) -> None:
        collected = 0
        pages_seen = 0
        reported_pages: int | None = None
        reported_elements: int | None = None
        ended_by_api = False
        for page_number in range(self.max_pages_per_score):
            payload: dict[str, Any] = {
                "filters": {"puanTuru": score_type},
                "page": page_number,
                "size": self.page_size,
            }
            if entity == "programs":
                payload.update({"sortBy": "basariSirasi", "direction": "ASC"})
            relative_path = f"{entity}/{score_type}/page_{page_number:06d}.json"
            data = self._load_or_fetch(
                endpoint=endpoint,
                method="POST",
                payload=payload,
                relative_path=relative_path,
                entity=entity,
                score_type=score_type,
                page_number=page_number,
            )
            if not isinstance(data, dict) or not isinstance(data.get("content"), list):
                raise CollectionError(f"{entity}/{score_type}/{page_number}: expected content[] response")
            rows = data["content"]
            if not all(isinstance(row, dict) for row in rows):
                raise CollectionError(f"{entity}/{score_type}/{page_number}: content contains non-object rows")
            reported_number = data.get("number")
            if isinstance(reported_number, int) and reported_number != page_number:
                raise CollectionError(
                    f"{entity}/{score_type}: requested page {page_number}, received page {reported_number}"
                )
            if page_number == 0:
                total_pages = data.get("totalPages")
                total_elements = data.get("totalElements")
                reported_pages = total_pages if isinstance(total_pages, int) else None
                reported_elements = total_elements if isinstance(total_elements, int) else None

            collected += len(rows)
            pages_seen += 1
            is_last = data.get("last") is True
            if not rows or is_last or (reported_pages is not None and page_number + 1 >= reported_pages):
                ended_by_api = True
                break

        complete_by_pages = (
            pages_seen >= reported_pages if reported_pages is not None else ended_by_api
        )
        complete_by_rows = reported_elements is None or collected == reported_elements
        coverage = {
            "entity": entity,
            "score_type": score_type,
            "pages_seen": pages_seen,
            "reported_total_pages": reported_pages,
            "records_seen": collected,
            "reported_total_elements": reported_elements,
            "complete_by_pages": complete_by_pages,
            "complete_by_records": complete_by_rows,
        }
        self.manifest["coverage"].append(coverage)
        self._save_manifest()
        if not complete_by_pages or not complete_by_rows:
            raise CollectionError(f"{entity}/{score_type}: archive is incomplete: {coverage}")

    def collect(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._save_manifest()
        try:
            for entity, endpoint in LOOKUPS:
                self._collect_lookup(entity, endpoint)
            for entity, endpoint in SEARCHES:
                for score_type in SCORE_TYPES:
                    self._collect_search(entity, endpoint, score_type)
            self.manifest["status"] = "completed"
        except Exception as exc:
            self.manifest["status"] = "partial"
            self.manifest["stopped_reason"] = f"{type(exc).__name__}: {exc}"
            print(f"Collection paused: {exc}", file=sys.stderr)
        finally:
            self.manifest["finished_at"] = utc_now()
            self.request_count = self.client.requests_made
            self.manifest["new_request_count"] = self.request_count
            self._save_manifest()
            self.client.close()
        return self.manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/yokatlas_full"))
    parser.add_argument("--delay", type=float, default=1.0, help="minimum seconds between HTTP attempts")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=5, help="maximum attempts per HTTP request")
    parser.add_argument("--max-requests", type=int, default=5000)
    parser.add_argument("--max-pages-per-score", type=int, default=10000)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--refresh", action="store_true", help="fetch cached pages again")
    args = parser.parse_args(argv)
    if args.retries < 1 or args.timeout <= 0:
        parser.error("retries must be positive and timeout must be greater than zero")

    collector = YokAtlasCollector(
        output_dir=args.output_dir,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        max_attempts=args.retries,
        max_requests=args.max_requests,
        max_pages_per_score=args.max_pages_per_score,
        page_size=args.page_size,
        refresh=args.refresh,
    )
    result = collector.collect()
    print(f"Run {result['run_id']}: {result['status']}; requests={result['new_request_count']}")
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

