import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
INPUT_URLS_PATH = ROOT / "docs" / "phases" / "phase-2" / "phase-2.1-input-urls.json"
ALLOWLIST_PATH = ROOT / "docs" / "phases" / "phase-1" / "allowlist-config.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.1-fetcher" / "output"
RAW_DIR = OUTPUT_DIR / "raw"
LATEST_OUTPUT_PATH = OUTPUT_DIR / "fetch-run-latest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    slug = url.replace("https://", "").replace("http://", "").replace("/", "_")
    return f"{slug}_{digest}.html"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dirs() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)


def fetch_url(url: str, timeout_seconds: int = 20) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "Milestone2-Fetcher/1.0 (+facts-only-rag)"
        },
    )
    fetched_at = iso_now()
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            http_status_code = response.getcode()
            fingerprint = hashlib.sha256(body).hexdigest()
            content_length = len(body)

            raw_path = RAW_DIR / safe_filename(url)
            raw_path.write_bytes(body)

            return {
                "url": url,
                "fetch_status": "success",
                "http_status_code": http_status_code,
                "fetched_at": fetched_at,
                "response_fingerprint": fingerprint,
                "content_type": content_type,
                "content_length": content_length,
                "error_message": None,
                "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            }
    except HTTPError as e:
        return {
            "url": url,
            "fetch_status": "failure",
            "http_status_code": e.code,
            "fetched_at": fetched_at,
            "response_fingerprint": "",
            "content_type": "",
            "content_length": 0,
            "error_message": f"HTTPError: {e.reason}",
            "raw_snapshot_path": None,
        }
    except URLError as e:
        return {
            "url": url,
            "fetch_status": "failure",
            "http_status_code": 0,
            "fetched_at": fetched_at,
            "response_fingerprint": "",
            "content_type": "",
            "content_length": 0,
            "error_message": f"URLError: {e.reason}",
            "raw_snapshot_path": None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "url": url,
            "fetch_status": "failure",
            "http_status_code": 0,
            "fetched_at": fetched_at,
            "response_fingerprint": "",
            "content_type": "",
            "content_length": 0,
            "error_message": f"Exception: {str(e)}",
            "raw_snapshot_path": None,
        }


def main() -> None:
    ensure_output_dirs()
    input_payload = load_json(INPUT_URLS_PATH)
    allowlist_payload = load_json(ALLOWLIST_PATH)

    input_urls = input_payload.get("urls", [])
    approved_urls = set(allowlist_payload.get("approved_urls", []))

    started_at = iso_now()
    results = []

    for url in input_urls:
        if url not in approved_urls:
            results.append(
                {
                    "url": url,
                    "fetch_status": "failure",
                    "http_status_code": 0,
                    "fetched_at": iso_now(),
                    "response_fingerprint": "",
                    "content_type": "",
                    "content_length": 0,
                    "error_message": "PolicyError: URL is not in exact-match allowlist",
                    "raw_snapshot_path": None,
                }
            )
            continue

        results.append(fetch_url(url))

    success_count = sum(1 for r in results if r["fetch_status"] == "success")
    failure_count = len(results) - success_count

    run_payload = {
        "phase": "2.1",
        "run_id": f"fetch-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "started_at": started_at,
        "completed_at": iso_now(),
        "allowlist_mode": allowlist_payload.get("mode", "exact_url_match"),
        "input_source": "docs/phases/phase-2/phase-2.1-input-urls.json",
        "results": results,
        "summary": {
            "total_urls": len(results),
            "success_count": success_count,
            "failure_count": failure_count,
        },
    }

    with LATEST_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(run_payload, f, indent=2)

    print(f"Wrote fetch run output to: {LATEST_OUTPUT_PATH}")
    print(f"Summary: success={success_count}, failure={failure_count}")


if __name__ == "__main__":
    main()
