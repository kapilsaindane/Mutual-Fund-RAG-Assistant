#!/usr/bin/env python3

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "output"
QUALITY_REPORT_PATH = OUTPUT_DIR / "quality-gate-report-latest.json"

# Phase output paths
FETCHER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.1-fetcher" / "output" / "fetch-run-latest.json"
EXTRACTOR_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.2-extractor" / "output" / "extraction-report-latest.json"
CLEANER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.3-cleaner" / "output" / "cleaning-report-latest.json"
CHUNKER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.4-chunker" / "output" / "chunking-report-latest.json"
EMBEDDER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.5-embedder" / "output" / "embeddings-latest.json"
INDEXER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.6-indexerr" / "output" / "index-report-latest.json"


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


class QualityGateChecker:
    def __init__(self):
        self.results = {}
        self.overall_status = "passed"
        
    def check_fetch_quality(self) -> dict:
        """Check fetch phase quality"""
        print("Checking fetch quality...")
        
        fetch_data = load_json(FETCHER_OUTPUT)
        if not fetch_data:
            return {
                "status": "failed",
                "error": "No fetch output found",
                "details": {}
            }
        
        results = fetch_data.get("results", [])
        summary = fetch_data.get("summary", {})
        
        # Quality checks
        failed_fetches = [r for r in results if r.get("fetch_status") != "success"]
        empty_responses = [r for r in results if r.get("content_length", 0) == 0]
        
        issues = []
        if failed_fetches:
            issues.append(f"{len(failed_fetches)} URLs failed to fetch")
        if empty_responses:
            issues.append(f"{len(empty_responses)} URLs returned empty content")
        
        success_rate = summary.get("success_count", 0) / max(summary.get("total_urls", 1), 1)
        
        status = "passed" if success_rate >= 0.95 and len(issues) == 0 else "failed"
        
        return {
            "status": status,
            "success_rate": success_rate,
            "total_urls": summary.get("total_urls", 0),
            "successful_fetches": summary.get("success_count", 0),
            "failed_fetches": len(failed_fetches),
            "empty_responses": len(empty_responses),
            "issues": issues,
            "details": {
                "failed_urls": [r["url"] for r in failed_fetches],
                "empty_urls": [r["url"] for r in empty_responses]
            }
        }
    
    def check_extraction_quality(self) -> dict:
        """Check extraction phase quality"""
        print("Checking extraction quality...")
        
        extraction_data = load_json(EXTRACTOR_OUTPUT)
        if not extraction_data:
            return {
                "status": "failed",
                "error": "No extraction output found",
                "details": {}
            }
        
        # Check for broken extractions
        extractions = extraction_data.get("extractions", [])
        failed_extractions = [e for e in extractions if e.get("status") != "success"]
        empty_extractions = [e for e in extractions if e.get("text_length", 0) == 0]
        
        issues = []
        if failed_extractions:
            issues.append(f"{len(failed_extractions)} extractions failed")
        if empty_extractions:
            issues.append(f"{len(empty_extractions)} extractions returned empty text")
        
        success_rate = len(extractions) - len(failed_extractions) / max(len(extractions), 1)
        
        status = "passed" if success_rate >= 0.95 and len(issues) == 0 else "failed"
        
        return {
            "status": status,
            "success_rate": success_rate,
            "total_extractions": len(extractions),
            "successful_extractions": len(extractions) - len(failed_extractions),
            "failed_extractions": len(failed_extractions),
            "empty_extractions": len(empty_extractions),
            "issues": issues,
            "details": {
                "failed_urls": [e["url"] for e in failed_extractions],
                "empty_urls": [e["url"] for e in empty_extractions]
            }
        }
    
    def check_cleaning_quality(self) -> dict:
        """Check cleaning phase quality"""
        print("Checking cleaning quality...")
        
        cleaning_data = load_json(CLEANER_OUTPUT)
        if not cleaning_data:
            return {
                "status": "failed",
                "error": "No cleaning output found",
                "details": {}
            }
        
        # Check for cleaning issues
        cleaned_chunks = cleaning_data.get("cleaned_chunks", [])
        empty_chunks = [c for c in cleaned_chunks if not c.get("text", "").strip()]
        very_short_chunks = [c for c in cleaned_chunks if len(c.get("text", "")) < 50]
        
        issues = []
        if empty_chunks:
            issues.append(f"{len(empty_chunks)} chunks are empty after cleaning")
        if len(very_short_chunks) > len(cleaned_chunks) * 0.1:  # More than 10% very short
            issues.append(f"{len(very_short_chunks)} chunks are very short (< 50 chars)")
        
        status = "passed" if len(empty_chunks) == 0 and len(issues) == 0 else "warning"
        
        return {
            "status": status,
            "total_chunks": len(cleaned_chunks),
            "empty_chunks": len(empty_chunks),
            "very_short_chunks": len(very_short_chunks),
            "issues": issues,
            "details": {
                "empty_chunk_ids": [c.get("chunk_id") for c in empty_chunks],
                "very_short_chunk_ids": [c.get("chunk_id") for c in very_short_chunks]
            }
        }
    
    def check_chunking_quality(self) -> dict:
        """Check chunking phase quality"""
        print("Checking chunking quality...")
        
        chunking_data = load_json(CHUNKER_OUTPUT)
        if not chunking_data:
            return {
                "status": "failed",
                "error": "No chunking output found",
                "details": {}
            }
        
        chunks = chunking_data.get("chunks", [])
        
        # Quality checks
        empty_chunks = [c for c in chunks if not c.get("text", "").strip()]
        duplicate_texts = {}
        text_hashes = {}
        
        for chunk in chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue
                
            # Simple hash for duplicate detection
            text_hash = hash(text)
            if text_hash in text_hashes:
                duplicate_texts[text_hash] = duplicate_texts.get(text_hash, []) + [chunk.get("chunk_id")]
            else:
                text_hashes[text_hash] = chunk.get("chunk_id")
        
        # Count duplicates (excluding the first occurrence)
        total_duplicates = sum(len(dup_ids) for dup_ids in duplicate_texts.values())
        
        # Check chunk sizes
        very_short_chunks = [c for c in chunks if len(c.get("text", "")) < 100]
        very_long_chunks = [c for c in chunks if len(c.get("text", "")) > 2000]
        
        issues = []
        if empty_chunks:
            issues.append(f"{len(empty_chunks)} chunks are empty")
        if total_duplicates > 0:
            issues.append(f"{total_duplicates} duplicate chunks found")
        if len(very_short_chunks) > len(chunks) * 0.05:  # More than 5% very short
            issues.append(f"{len(very_short_chunks)} chunks are very short (< 100 chars)")
        if len(very_long_chunks) > len(chunks) * 0.1:  # More than 10% very long
            issues.append(f"{len(very_long_chunks)} chunks are very long (> 2000 chars)")
        
        status = "passed" if len(empty_chunks) == 0 and total_duplicates == 0 and len(issues) == 0 else "warning"
        
        return {
            "status": status,
            "total_chunks": len(chunks),
            "empty_chunks": len(empty_chunks),
            "duplicate_chunks": total_duplicates,
            "very_short_chunks": len(very_short_chunks),
            "very_long_chunks": len(very_long_chunks),
            "issues": issues,
            "details": {
                "empty_chunk_ids": [c.get("chunk_id") for c in empty_chunks],
                "duplicate_groups": {str(k): v for k, v in duplicate_texts.items() if v},
                "very_short_chunk_ids": [c.get("chunk_id") for c in very_short_chunks],
                "very_long_chunk_ids": [c.get("chunk_id") for c in very_long_chunks]
            }
        }
    
    def check_embedding_quality(self) -> dict:
        """Check embedding phase quality"""
        print("Checking embedding quality...")
        
        embedding_data = load_json(EMBEDDER_OUTPUT)
        if not embedding_data:
            return {
                "status": "failed",
                "error": "No embedding output found",
                "details": {}
            }
        
        chunks = embedding_data.get("chunks", [])
        embedding_dim = embedding_data.get("embedding_dim")
        
        # Quality checks
        chunks_without_embeddings = [c for c in chunks if not c.get("embedding")]
        invalid_embeddings = []
        
        for chunk in chunks:
            embedding = chunk.get("embedding", [])
            if not isinstance(embedding, list) or len(embedding) != embedding_dim:
                invalid_embeddings.append(chunk.get("chunk_id"))
        
        issues = []
        if chunks_without_embeddings:
            issues.append(f"{len(chunks_without_embeddings)} chunks missing embeddings")
        if invalid_embeddings:
            issues.append(f"{len(invalid_embeddings)} chunks have invalid embeddings")
        if not embedding_dim:
            issues.append("Embedding dimension not specified")
        
        status = "passed" if len(chunks_without_embeddings) == 0 and len(invalid_embeddings) == 0 and len(issues) == 0 else "failed"
        
        return {
            "status": status,
            "total_chunks": len(chunks),
            "chunks_with_embeddings": len(chunks) - len(chunks_without_embeddings),
            "chunks_without_embeddings": len(chunks_without_embeddings),
            "invalid_embeddings": len(invalid_embeddings),
            "embedding_dimension": embedding_dim,
            "issues": issues,
            "details": {
                "chunks_without_embeddings": [c.get("chunk_id") for c in chunks_without_embeddings],
                "invalid_embedding_ids": invalid_embeddings
            }
        }
    
    def check_index_quality(self) -> dict:
        """Check index phase quality"""
        print("Checking index quality...")
        
        index_data = load_json(INDEXER_OUTPUT)
        if not index_data:
            return {
                "status": "failed",
                "error": "No index output found",
                "details": {}
            }
        
        summary = index_data.get("summary", {})
        metadata_validation = index_data.get("metadata_filter_validation", {})
        
        # Quality checks
        total_input = summary.get("total_input_chunks", 0)
        total_indexed = summary.get("total_indexed_chunks", 0)
        
        issues = []
        if total_indexed < total_input:
            issues.append(f"{total_input - total_indexed} chunks failed to index")
        
        # Check metadata filter validation
        failed_filters = [k for k, v in metadata_validation.items() if not v]
        if failed_filters:
            issues.append(f"Metadata filters failed for: {', '.join(failed_filters)}")
        
        status = "passed" if total_indexed == total_input and len(failed_filters) == 0 and len(issues) == 0 else "failed"
        
        return {
            "status": status,
            "total_input_chunks": total_input,
            "total_indexed_chunks": total_indexed,
            "indexing_success_rate": total_indexed / max(total_input, 1),
            "metadata_filter_validation": metadata_validation,
            "failed_metadata_filters": failed_filters,
            "issues": issues,
            "details": {}
        }
    
    def run_all_checks(self) -> dict:
        """Run all quality gate checks"""
        print("Running all quality gate checks...")
        
        self.results = {
            "fetch": self.check_fetch_quality(),
            "extraction": self.check_extraction_quality(),
            "cleaning": self.check_cleaning_quality(),
            "chunking": self.check_chunking_quality(),
            "embedding": self.check_embedding_quality(),
            "index": self.check_index_quality()
        }
        
        # Determine overall status
        failed_gates = [name for name, result in self.results.items() if result.get("status") == "failed"]
        warning_gates = [name for name, result in self.results.items() if result.get("status") == "warning"]
        
        if failed_gates:
            self.overall_status = "failed"
        elif warning_gates:
            self.overall_status = "warning"
        else:
            self.overall_status = "passed"
        
        return {
            "overall_status": self.overall_status,
            "failed_gates": failed_gates,
            "warning_gates": warning_gates,
            "passed_gates": [name for name, result in self.results.items() if result.get("status") == "passed"],
            "gate_results": self.results,
            "summary": {
                "total_gates": len(self.results),
                "passed_gates": len([r for r in self.results.values() if r.get("status") == "passed"]),
                "warning_gates": len(warning_gates),
                "failed_gates": len(failed_gates)
            }
        }


def main():
    """Run quality gate checks"""
    print("Starting quality gate checks...")
    
    checker = QualityGateChecker()
    results = checker.run_all_checks()
    
    # Generate report
    report = {
        "phase": "2.7",
        "check_type": "quality_gates",
        "checked_at": iso_now(),
        "overall_status": results["overall_status"],
        "summary": results["summary"],
        "gate_results": results["gate_results"],
        "failed_gates": results["failed_gates"],
        "warning_gates": results["warning_gates"],
        "passed_gates": results["passed_gates"]
    }
    
    save_json(report, QUALITY_REPORT_PATH)
    
    # Print summary
    print(f"\nQuality Gate Summary:")
    print(f"- Overall Status: {results['overall_status'].upper()}")
    print(f"- Total Gates: {results['summary']['total_gates']}")
    print(f"- Passed: {results['summary']['passed_gates']}")
    print(f"- Warnings: {results['summary']['warning_gates']}")
    print(f"- Failed: {results['summary']['failed_gates']}")
    
    if results["failed_gates"]:
        print(f"\nFailed Gates:")
        for gate in results["failed_gates"]:
            result = results["gate_results"][gate]
            issues = result.get("issues", [])
            print(f"  [FAIL] {gate}: {', '.join(issues)}")
    
    if results["warning_gates"]:
        print(f"\nWarning Gates:")
        for gate in results["warning_gates"]:
            result = results["gate_results"][gate]
            issues = result.get("issues", [])
            print(f"  [WARN] {gate}: {', '.join(issues)}")
    
    print(f"\nDetailed report saved to: {QUALITY_REPORT_PATH}")
    
    # Exit with error code if any gates failed
    if results["overall_status"] == "failed":
        print("Quality gates failed!")
        sys.exit(1)
    elif results["overall_status"] == "warning":
        print("Quality gates passed with warnings.")
        sys.exit(0)
    else:
        print("All quality gates passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
