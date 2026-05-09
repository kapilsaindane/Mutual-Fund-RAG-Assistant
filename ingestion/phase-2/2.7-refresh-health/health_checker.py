#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.7-refresh-health" / "output"
HEALTH_REPORT_PATH = OUTPUT_DIR / "health-report-latest.json"

# Phase output paths
EMBEDDER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.5-embedder" / "output" / "embeddings-latest.json"
INDEXER_OUTPUT = ROOT / "ingestion" / "phase-2" / "2.6-indexerr" / "output" / "index-report-latest.json"
CHROMA_DIR = ROOT / "ingestion" / "phase-2" / "2.6-indexerr" / "chroma-data"


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


class HealthChecker:
    def __init__(self):
        self.results = {}
        self.overall_health = "healthy"
        
    def check_embedding_health(self) -> dict:
        """Check embedding system health"""
        print("Checking embedding health...")
        
        embedding_data = load_json(EMBEDDER_OUTPUT)
        if not embedding_data:
            return {
                "status": "unhealthy",
                "error": "No embedding data found",
                "details": {}
            }
        
        chunks = embedding_data.get("chunks", [])
        embedding_dim = embedding_data.get("embedding_dim")
        
        health_issues = []
        
        # Check if we have any chunks
        if not chunks:
            health_issues.append("No chunks found in embedding data")
            return {
                "status": "unhealthy",
                "total_chunks": 0,
                "embedding_dimension": embedding_dim,
                "health_issues": health_issues,
                "details": {}
            }
        
        # Check embedding consistency
        chunks_with_embeddings = 0
        embedding_dimensions = set()
        embedding_stats = {
            "min_length": float('inf'),
            "max_length": 0,
            "total_length": 0,
            "zero_vectors": 0
        }
        
        for chunk in chunks:
            embedding = chunk.get("embedding", [])
            if embedding:
                chunks_with_embeddings += 1
                embedding_dimensions.add(len(embedding))
                
                # Calculate embedding statistics
                embedding_length = len(embedding)
                embedding_stats["min_length"] = min(embedding_stats["min_length"], embedding_length)
                embedding_stats["max_length"] = max(embedding_stats["max_length"], embedding_length)
                embedding_stats["total_length"] += embedding_length
                
                # Check for zero vectors (all zeros)
                if all(abs(x) < 1e-10 for x in embedding):
                    embedding_stats["zero_vectors"] += 1
        
        # Health checks
        if chunks_with_embeddings < len(chunks):
            health_issues.append(f"{len(chunks) - chunks_with_embeddings} chunks missing embeddings")
        
        if len(embedding_dimensions) > 1:
            health_issues.append(f"Inconsistent embedding dimensions: {embedding_dimensions}")
        
        if embedding_stats["zero_vectors"] > 0:
            health_issues.append(f"{embedding_stats['zero_vectors']} chunks have zero vectors")
        
        # Check if embedding dimension is reasonable
        if embedding_dim and (embedding_dim < 100 or embedding_dim > 2000):
            health_issues.append(f"Unusual embedding dimension: {embedding_dim}")
        
        status = "healthy" if len(health_issues) == 0 else "degraded" if len(health_issues) <= 2 else "unhealthy"
        
        embedding_stats["avg_length"] = embedding_stats["total_length"] / max(chunks_with_embeddings, 1)
        
        return {
            "status": status,
            "total_chunks": len(chunks),
            "chunks_with_embeddings": chunks_with_embeddings,
            "embedding_coverage": chunks_with_embeddings / len(chunks),
            "embedding_dimension": embedding_dim,
            "consistent_dimensions": len(embedding_dimensions) <= 1,
            "embedding_stats": embedding_stats,
            "health_issues": health_issues,
            "details": {
                "dimension_variance": list(embedding_dimensions)
            }
        }
    
    def check_index_health(self) -> dict:
        """Check vector index health"""
        print("Checking index health...")
        
        try:
            import chromadb
        except ImportError:
            return {
                "status": "unhealthy",
                "error": "chromadb not available",
                "details": {}
            }
        
        index_data = load_json(INDEXER_OUTPUT)
        if not index_data:
            return {
                "status": "unhealthy",
                "error": "No index data found",
                "details": {}
            }
        
        health_issues = []
        
        try:
            # Try to connect to ChromaDB
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            collection_name = index_data.get("collection_name", "mutual_fund_faq_phase2")
            
            try:
                collection = client.get_collection(collection_name)
            except Exception:
                # Collection might not exist, try to create it
                collection = client.get_or_create_collection(collection_name)
            
            # Get collection stats
            total_count = collection.count()
            
            # Test basic query functionality
            try:
                # Simple query to test index functionality
                test_results = collection.query(
                    query_texts=["test"],
                    n_results=1
                )
                query_working = True
            except Exception as e:
                query_working = False
                health_issues.append(f"Query functionality failed: {str(e)}")
            
            # Test metadata filters
            try:
                filter_results = collection.get(
                    where={"scheme": "test"},
                    limit=1
                )
                filters_working = True
            except Exception as e:
                filters_working = False
                health_issues.append(f"Metadata filters failed: {str(e)}")
            
            # Check index consistency
            summary = index_data.get("summary", {})
            expected_chunks = summary.get("total_indexed_chunks", 0)
            
            if total_count != expected_chunks:
                health_issues.append(f"Index count mismatch: expected {expected_chunks}, found {total_count}")
            
            # Check metadata filter validation
            metadata_validation = index_data.get("metadata_filter_validation", {})
            failed_filters = [k for k, v in metadata_validation.items() if not v]
            if failed_filters:
                health_issues.append(f"Failed metadata filters: {failed_filters}")
            
            # Get collection metadata
            collection_metadata = {
                "name": collection_name,
                "count": total_count,
                "query_working": query_working,
                "filters_working": filters_working
            }
            
            status = "healthy" if len(health_issues) == 0 else "degraded" if len(health_issues) <= 2 else "unhealthy"
            
            return {
                "status": status,
                "collection_metadata": collection_metadata,
                "index_consistency": total_count == expected_chunks,
                "expected_chunks": expected_chunks,
                "actual_chunks": total_count,
                "query_functionality": query_working,
                "filter_functionality": filters_working,
                "metadata_validation": metadata_validation,
                "health_issues": health_issues,
                "details": {
                    "failed_metadata_filters": failed_filters
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Failed to connect to index: {str(e)}",
                "details": {}
            }
    
    def check_data_freshness(self) -> dict:
        """Check data freshness"""
        print("Checking data freshness...")
        
        embedding_data = load_json(EMBEDDER_OUTPUT)
        index_data = load_json(INDEXER_OUTPUT)
        
        health_issues = []
        
        # Check embedding data freshness
        embedding_timestamp = None
        if embedding_data:
            # Look for timestamp in various possible fields
            embedding_timestamp = (
                embedding_data.get("generated_at") or
                embedding_data.get("timestamp") or
                embedding_data.get("created_at")
            )
        
        # Check index data freshness
        index_timestamp = None
        if index_data:
            index_timestamp = (
                index_data.get("generated_at") or
                index_data.get("timestamp") or
                index_data.get("created_at")
            )
        
        # Calculate age in hours
        now = datetime.now(timezone.utc)
        freshness_data = {}
        
        if embedding_timestamp:
            try:
                embedding_time = datetime.fromisoformat(embedding_timestamp.replace('Z', '+00:00'))
                embedding_age_hours = (now - embedding_time).total_seconds() / 3600
                freshness_data["embedding_age_hours"] = embedding_age_hours
                
                if embedding_age_hours > 48:  # Older than 48 hours
                    health_issues.append(f"Embedding data is {embedding_age_hours:.1f} hours old")
                
            except Exception:
                health_issues.append("Invalid embedding timestamp format")
        
        if index_timestamp:
            try:
                index_time = datetime.fromisoformat(index_timestamp.replace('Z', '+00:00'))
                index_age_hours = (now - index_time).total_seconds() / 3600
                freshness_data["index_age_hours"] = index_age_hours
                
                if index_age_hours > 48:  # Older than 48 hours
                    health_issues.append(f"Index data is {index_age_hours:.1f} hours old")
                
            except Exception:
                health_issues.append("Invalid index timestamp format")
        
        # Check if index is newer than embeddings (should be)
        if embedding_timestamp and index_timestamp:
            try:
                embedding_time = datetime.fromisoformat(embedding_timestamp.replace('Z', '+00:00'))
                index_time = datetime.fromisoformat(index_timestamp.replace('Z', '+00:00'))
                
                if index_time < embedding_time:
                    health_issues.append("Index is older than embedding data")
                
            except Exception:
                pass  # Already caught above
        
        status = "healthy" if len(health_issues) == 0 else "degraded" if len(health_issues) <= 1 else "unhealthy"
        
        return {
            "status": status,
            "embedding_timestamp": embedding_timestamp,
            "index_timestamp": index_timestamp,
            "freshness_data": freshness_data,
            "health_issues": health_issues,
            "details": {}
        }
    
    def check_system_resources(self) -> dict:
        """Check system resources and disk space"""
        print("Checking system resources...")
        
        health_issues = []
        resource_data = {}
        
        try:
            import shutil
            
            # Check disk space for key directories
            key_dirs = [
                CHROMA_DIR,
                ROOT / "ingestion" / "phase-2" / "output",
                ROOT / "ingestion" / "phase-2" / "2.1-fetcher" / "output" / "raw"
            ]
            
            for dir_path in key_dirs:
                if dir_path.exists():
                    total, used, free = shutil.disk_usage(dir_path)
                    free_gb = free / (1024**3)
                    used_gb = used / (1024**3)
                    total_gb = total / (1024**3)
                    
                    resource_data[str(dir_path.relative_to(ROOT)).replace("\\", "/")] = {
                        "free_gb": round(free_gb, 2),
                        "used_gb": round(used_gb, 2),
                        "total_gb": round(total_gb, 2),
                        "usage_percent": round((used_gb / total_gb) * 100, 2)
                    }
                    
                    if free_gb < 1:  # Less than 1GB free
                        health_issues.append(f"Low disk space in {dir_path.name}: {free_gb:.1f}GB free")
            
        except Exception as e:
            health_issues.append(f"Failed to check system resources: {str(e)}")
        
        status = "healthy" if len(health_issues) == 0 else "degraded" if len(health_issues) <= 1 else "unhealthy"
        
        return {
            "status": status,
            "resource_data": resource_data,
            "health_issues": health_issues,
            "details": {}
        }
    
    def run_all_health_checks(self) -> dict:
        """Run all health checks"""
        print("Running all health checks...")
        
        self.results = {
            "embedding": self.check_embedding_health(),
            "index": self.check_index_health(),
            "data_freshness": self.check_data_freshness(),
            "system_resources": self.check_system_resources()
        }
        
        # Determine overall health
        unhealthy_components = [name for name, result in self.results.items() if result.get("status") == "unhealthy"]
        degraded_components = [name for name, result in self.results.items() if result.get("status") == "degraded"]
        
        if unhealthy_components:
            self.overall_health = "unhealthy"
        elif degraded_components:
            self.overall_health = "degraded"
        else:
            self.overall_health = "healthy"
        
        return {
            "overall_health": self.overall_health,
            "unhealthy_components": unhealthy_components,
            "degraded_components": degraded_components,
            "healthy_components": [name for name, result in self.results.items() if result.get("status") == "healthy"],
            "health_results": self.results,
            "summary": {
                "total_components": len(self.results),
                "healthy_components": len([r for r in self.results.values() if r.get("status") == "healthy"]),
                "degraded_components": len(degraded_components),
                "unhealthy_components": len(unhealthy_components)
            }
        }


def main():
    """Run health checks"""
    print("Starting system health checks...")
    
    checker = HealthChecker()
    results = checker.run_all_health_checks()
    
    # Generate health report
    report = {
        "phase": "2.7",
        "check_type": "health_check",
        "checked_at": iso_now(),
        "overall_health": results["overall_health"],
        "summary": results["summary"],
        "health_results": results["health_results"],
        "unhealthy_components": results["unhealthy_components"],
        "degraded_components": results["degraded_components"],
        "healthy_components": results["healthy_components"]
    }
    
    save_json(report, HEALTH_REPORT_PATH)
    
    # Print summary
    print(f"\nHealth Check Summary:")
    print(f"- Overall Health: {results['overall_health'].upper()}")
    print(f"- Total Components: {results['summary']['total_components']}")
    print(f"- Healthy: {results['summary']['healthy_components']}")
    print(f"- Degraded: {results['summary']['degraded_components']}")
    print(f"- Unhealthy: {results['summary']['unhealthy_components']}")
    
    if results["unhealthy_components"]:
        print(f"\nUnhealthy Components:")
        for component in results["unhealthy_components"]:
            result = results["health_results"][component]
            issues = result.get("health_issues", [])
            print(f"  ❌ {component}: {', '.join(issues)}")
    
    if results["degraded_components"]:
        print(f"\nDegraded Components:")
        for component in results["degraded_components"]:
            result = results["health_results"][component]
            issues = result.get("health_issues", [])
            print(f"  ⚠️  {component}: {', '.join(issues)}")
    
    print(f"\nDetailed health report saved to: {HEALTH_REPORT_PATH}")
    
    # Exit with appropriate code
    if results["overall_health"] == "unhealthy":
        print("System health check failed!")
        sys.exit(1)
    elif results["overall_health"] == "degraded":
        print("System health check passed with warnings.")
        sys.exit(0)
    else:
        print("All system health checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
