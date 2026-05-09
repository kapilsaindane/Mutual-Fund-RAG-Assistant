#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
INPUT_URLS_PATH = ROOT / "docs" / "phases" / "phase-2" / "phase-2.1-input-urls.json"
ALLOWLIST_PATH = ROOT / "docs" / "phases" / "phase-1" / "allowlist-config.json"
STATE_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "state"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "output"
LAST_FETCH_STATE = STATE_DIR / "last_fetch_state.json"
CHANGE_REPORT_PATH = OUTPUT_DIR / "change-report-latest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def fetch_content_fingerprint(url: str, timeout_seconds: int = 20) -> str:
    """Fetch content and return SHA256 fingerprint"""
    req = Request(
        url,
        headers={
            "User-Agent": "Milestone2-ChangeDetector/1.0 (+facts-only-rag)"
        },
    )
    
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            body = response.read()
            return hashlib.sha256(body).hexdigest()
    except (HTTPError, URLError) as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return ""
    except Exception as e:
        print(f"Warning: Error fetching {url}: {e}")
        return ""


def detect_changes(urls: list, force_refresh: bool = False) -> dict:
    """Detect changes in source URLs"""
    previous_state = load_json(LAST_FETCH_STATE)
    current_state = {}
    changed_urls = []
    failed_urls = []
    
    for url in urls:
        print(f"Checking URL: {url}")
        
        if force_refresh:
            print(f"Force refresh enabled - marking {url} as changed")
            changed_urls.append(url)
            current_fingerprint = fetch_content_fingerprint(url)
            if current_fingerprint:
                current_state[url] = {
                    "fingerprint": current_fingerprint,
                    "last_checked": iso_now(),
                    "status": "success"
                }
            else:
                current_state[url] = {
                    "fingerprint": "",
                    "last_checked": iso_now(),
                    "status": "failed"
                }
                failed_urls.append(url)
            continue
            
        current_fingerprint = fetch_content_fingerprint(url)
        
        if current_fingerprint == "":
            # Failed to fetch
            current_state[url] = {
                "fingerprint": "",
                "last_checked": iso_now(),
                "status": "failed"
            }
            failed_urls.append(url)
            continue
            
        current_state[url] = {
            "fingerprint": current_fingerprint,
            "last_checked": iso_now(),
            "status": "success"
        }
        
        # Check if URL is new or changed
        if url not in previous_state:
            print(f"New URL detected: {url}")
            changed_urls.append(url)
        elif previous_state[url].get("fingerprint", "") != current_fingerprint:
            print(f"Content changed for: {url}")
            changed_urls.append(url)
        else:
            print(f"No changes for: {url}")
    
    # Save current state
    save_json(current_state, LAST_FETCH_STATE)
    
    # Generate change report
    report = {
        "phase": "2.7",
        "check_type": "change_detection",
        "checked_at": iso_now(),
        "force_refresh": force_refresh,
        "summary": {
            "total_urls": len(urls),
            "changed_urls": len(changed_urls),
            "failed_urls": len(failed_urls),
            "unchanged_urls": len(urls) - len(changed_urls) - len(failed_urls)
        },
        "changed_urls": changed_urls,
        "failed_urls": failed_urls,
        "has_changes": len(changed_urls) > 0 or force_refresh,
        "previous_state_file": str(LAST_FETCH_STATE.relative_to(ROOT)).replace("\\", "/")
    }
    
    save_json(report, CHANGE_REPORT_PATH)
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Detect changes in source URLs")
    parser.add_argument("--force-refresh", type=str, default="false", 
                       help="Force refresh all URLs (true/false)")
    parser.add_argument("--output-dir", type=str, default=None,
                       help="Output directory for reports (overrides default)")
    
    args = parser.parse_args()
    
    force_refresh = args.force_refresh.lower() in ("true", "1", "yes")
    
    if args.output_dir:
        global OUTPUT_DIR, CHANGE_REPORT_PATH
        OUTPUT_DIR = Path(args.output_dir)
        CHANGE_REPORT_PATH = OUTPUT_DIR / "change-report-latest.json"
    
    # Load URLs and allowlist
    input_payload = load_json(INPUT_URLS_PATH)
    allowlist_payload = load_json(ALLOWLIST_PATH)
    
    urls = input_payload.get("urls", [])
    approved_urls = set(allowlist_payload.get("approved_urls", []))
    
    # Filter to approved URLs only
    approved_urls_list = [url for url in urls if url in approved_urls]
    
    if len(approved_urls_list) != len(urls):
        print(f"Warning: Filtered {len(urls) - len(approved_urls_list)} non-approved URLs")
    
    print(f"Checking {len(approved_urls_list)} approved URLs...")
    
    # Detect changes
    report = detect_changes(approved_urls_list, force_refresh)
    
    # Output results for GitHub Actions
    print(f"::set-output name=has_changes::{report['has_changes']}")
    print(f"::set-output name=changed_urls::{','.join(report['changed_urls'])}")
    print(f"::set-output name=force_refresh::{force_refresh}")
    
    print(f"\nChange Detection Summary:")
    print(f"- Total URLs: {report['summary']['total_urls']}")
    print(f"- Changed URLs: {report['summary']['changed_urls']}")
    print(f"- Failed URLs: {report['summary']['failed_urls']}")
    print(f"- Unchanged URLs: {report['summary']['unchanged_urls']}")
    print(f"- Has changes: {report['has_changes']}")
    
    if report['changed_urls']:
        print(f"\nChanged URLs:")
        for url in report['changed_urls']:
            print(f"  - {url}")
    
    if report['failed_urls']:
        print(f"\nFailed URLs:")
        for url in report['failed_urls']:
            print(f"  - {url}")
    
    # Exit with error code if there are failed URLs
    if report['summary']['failed_urls'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
