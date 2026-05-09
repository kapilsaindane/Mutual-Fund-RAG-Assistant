#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INPUT_URLS_PATH = ROOT / "docs" / "phases" / "phase-2" / "phase-2.1-input-urls.json"
ALLOWLIST_PATH = ROOT / "docs" / "phases" / "phase-1" / "allowlist-config.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "output"
PIPELINE_REPORT_PATH = OUTPUT_DIR / "pipeline-report-latest.json"


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


def run_phase_script(phase_dir: str, script_name: str) -> dict:
    """Run a phase script and return the result"""
    script_path = ROOT / "ingestion" / "phase-2" / phase_dir / f"{script_name}.py"
    
    if not script_path.exists():
        return {
            "status": "skipped",
            "error": f"Script not found: {script_path}"
        }
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout per phase
        )
        
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "error": "Script execution timed out"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def create_temp_input_urls(changed_urls: list, all_urls: list, temp_path: Path) -> None:
    """Create temporary input URLs file with only changed URLs"""
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    # If no changed URLs, use all URLs for full refresh
    urls_to_process = changed_urls if changed_urls else all_urls
    
    input_data = {
        "urls": urls_to_process,
        "created_for": "incremental_refresh",
        "created_at": iso_now(),
        "changed_urls_count": len(changed_urls),
        "total_urls_count": len(all_urls)
    }
    
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(input_data, f, indent=2)


def backup_existing_outputs() -> dict:
    """Backup existing outputs before refresh"""
    backup_dir = ROOT / "ingestion" / "phase-2" / "backups" / f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    backed_up = {}
    output_dirs = [
        "2.1-fetcher/output",
        "2.2-extractor/output", 
        "2.3-cleaner/output",
        "2.4-chunker/output",
        "2.5-embedder/output",
        "2.6-indexerr/output"
    ]
    
    for dir_path in output_dirs:
        source_dir = ROOT / "ingestion" / "phase-2" / dir_path
        if source_dir.exists():
            target_dir = backup_dir / dir_path
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
            backed_up[dir_path] = str(target_dir.relative_to(ROOT)).replace("\\", "/")
    
    return {
        "backup_created": True,
        "backup_directory": str(backup_dir.relative_to(ROOT)).replace("\\", "/"),
        "backed_up_directories": backed_up
    }


def run_incremental_pipeline(changed_urls: list, force_refresh: bool) -> dict:
    """Run the ingestion pipeline with incremental or full refresh"""
    
    # Load original URLs
    input_payload = load_json(INPUT_URLS_PATH)
    allowlist_payload = load_json(ALLOWLIST_PATH)
    
    all_urls = input_payload.get("urls", [])
    approved_urls = set(allowlist_payload.get("approved_urls", []))
    
    # Filter to approved URLs
    all_approved_urls = [url for url in all_urls if url in approved_urls]
    changed_approved_urls = [url for url in changed_urls if url in approved_urls] if changed_urls else []
    
    # Create temporary input file
    temp_input_path = ROOT / "ingestion" / "phase-2" / "temp-input-urls.json"
    create_temp_input_urls(changed_approved_urls, all_approved_urls, temp_input_path)
    
    # Backup existing outputs
    backup_info = backup_existing_outputs()
    
    # Phase execution results
    phase_results = {}
    
    # Define pipeline phases in order
    phases = [
        ("2.1-fetcher", "fetcher"),
        ("2.2-extractor", "extractor"),
        ("2.3-cleaner", "cleaner"),
        ("2.4-chunker", "chunker"),
        ("2.5-embedder", "embedder"),
        ("2.6-indexerr", "indexerr")
    ]
    
    started_at = iso_now()
    
    # Run each phase
    for phase_dir, script_name in phases:
        print(f"Running {phase_dir}/{script_name}.py...")
        
        # For incremental updates, we might need to handle existing data differently
        # For now, we run the full pipeline on changed URLs
        result = run_phase_script(phase_dir, script_name)
        phase_results[phase_dir] = result
        
        if result["status"] == "failed":
            print(f"Phase {phase_dir} failed: {result.get('stderr', 'Unknown error')}")
            # Continue with other phases for now, but mark the pipeline as failed
        elif result["status"] == "timeout":
            print(f"Phase {phase_dir} timed out")
        elif result["status"] == "error":
            print(f"Phase {phase_dir} encountered error: {result.get('error', 'Unknown error')}")
        else:
            print(f"Phase {phase_dir} completed successfully")
    
    completed_at = iso_now()
    
    # Clean up temporary file
    if temp_input_path.exists():
        temp_input_path.unlink()
    
    # Generate pipeline report
    successful_phases = sum(1 for r in phase_results.values() if r["status"] == "success")
    failed_phases = len(phase_results) - successful_phases
    
    report = {
        "phase": "2.7",
        "pipeline_type": "incremental" if changed_urls and not force_refresh else "full",
        "started_at": started_at,
        "completed_at": completed_at,
        "force_refresh": force_refresh,
        "input_summary": {
            "total_approved_urls": len(all_approved_urls),
            "changed_urls": len(changed_approved_urls),
            "processed_urls": len(changed_approved_urls) if changed_approved_urls else len(all_approved_urls)
        },
        "backup_info": backup_info,
        "phase_results": phase_results,
        "summary": {
            "total_phases": len(phases),
            "successful_phases": successful_phases,
            "failed_phases": failed_phases,
            "pipeline_status": "success" if failed_phases == 0 else "failed"
        }
    }
    
    save_json(report, PIPELINE_REPORT_PATH)
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Run incremental refresh pipeline")
    parser.add_argument("--changed-urls", type=str, default="",
                       help="Comma-separated list of changed URLs")
    parser.add_argument("--force-refresh", type=str, default="false",
                       help="Force full refresh (true/false)")
    
    args = parser.parse_args()
    
    force_refresh = args.force_refresh.lower() in ("true", "1", "yes")
    changed_urls = [url.strip() for url in args.changed_urls.split(",") if url.strip()] if args.changed_urls else []
    
    print(f"Starting refresh pipeline...")
    print(f"Force refresh: {force_refresh}")
    print(f"Changed URLs: {len(changed_urls)}")
    
    if changed_urls:
        print("Changed URLs:")
        for url in changed_urls:
            print(f"  - {url}")
    
    # Run the pipeline
    report = run_incremental_pipeline(changed_urls, force_refresh)
    
    print(f"\nPipeline Summary:")
    print(f"- Pipeline type: {report['pipeline_type']}")
    print(f"- Total phases: {report['summary']['total_phases']}")
    print(f"- Successful phases: {report['summary']['successful_phases']}")
    print(f"- Failed phases: {report['summary']['failed_phases']}")
    print(f"- Pipeline status: {report['summary']['pipeline_status']}")
    print(f"- URLs processed: {report['input_summary']['processed_urls']}")
    
    # Show phase details
    for phase, result in report["phase_results"].items():
        status_icon = "[OK]" if result["status"] == "success" else "[FAIL]"
        print(f"{status_icon} {phase}: {result['status']}")
    
    # Exit with error code if pipeline failed
    if report['summary']['pipeline_status'] == 'failed':
        print(f"\nPipeline failed. Check the detailed report at: {PIPELINE_REPORT_PATH}")
        sys.exit(1)
    else:
        print(f"\nPipeline completed successfully!")
        print(f"Report saved to: {PIPELINE_REPORT_PATH}")


if __name__ == "__main__":
    main()
