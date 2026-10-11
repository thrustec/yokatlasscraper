# Scraper foundation

The scraper is organized around reusable HTTP and archive helpers plus one adapter per source. YÖK Atlas is the first adapter. New public sources can reuse the common client and archive code without changing the YÖK Atlas endpoint logic.

## YÖK Atlas collector

From the repository root, install the scraper dependency and run:

```powershell
python -m pip install -r scraper/requirements.txt
python -m scraper.yokatlas.collector --output-dir outputs/yokatlas_full
```

The default output keeps the `complete_data` directory layout expected by `scripts/database/load_archive.py`. It stores each successful JSON response body as received, then records endpoint, request payload, page, score type, timestamp, byte count, and SHA-256 in `collection_manifest.json`.

The collector waits at least one second between HTTP attempts, retries network errors, HTTP 429, and HTTP 5xx responses with bounded backoff, and stops on access restrictions. Existing valid page files are reused on reruns; pass `--refresh` to request them again. A partial run is recorded in the manifest and exits with a nonzero status.

This collector only reads the known public YÖK Atlas JSON endpoints. It does not attempt to bypass authentication, CAPTCHA, or other access controls. Review the manifest's page and record totals before running the archive importer.

