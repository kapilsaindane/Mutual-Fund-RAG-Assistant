import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "ingestion" / "phase-2" / "2.5-embedder" / "output" / "embeddings-latest.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.6-indexerr" / "output"
REPORT_PATH = OUTPUT_DIR / "index-report-latest.json"
CHROMA_DIR = ROOT / "ingestion" / "phase-2" / "2.6-indexerr" / "chroma-data"
COLLECTION_NAME = "mutual_fund_faq_phase2"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_chroma():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "chromadb is not installed. Install it with: pip install chromadb"
        ) from exc
    return chromadb


def safe_metadata(meta: dict) -> dict:
    # Chroma metadata supports scalar JSON-like types.
    out = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    chunks = payload.get("chunks", [])
    if not chunks:
        raise RuntimeError("No chunks found in embeddings input.")

    chromadb = load_chroma()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Rebuild collection for deterministic runs.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001
        pass
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for item in chunks:
        ids.append(item["chunk_id"])
        documents.append(item["text"])
        embeddings.append(item["embedding"])
        meta = safe_metadata(item.get("metadata", {}))
        # Ensure explicit filter keys exist.
        meta.setdefault("scheme", "")
        meta.setdefault("doc_type", "")
        meta.setdefault("source_url", "")
        metadatas.append(meta)

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    total_indexed = collection.count()

    # Validate metadata filters are indexable.
    sample_source = metadatas[0]["source_url"] if metadatas else ""
    sample_scheme = metadatas[0]["scheme"] if metadatas else ""
    sample_doc_type = metadatas[0]["doc_type"] if metadatas else ""

    filter_checks = {
        "scheme": len(collection.get(where={"scheme": sample_scheme}, limit=3).get("ids", [])) > 0 if sample_scheme else False,
        "doc_type": len(collection.get(where={"doc_type": sample_doc_type}, limit=3).get("ids", [])) > 0 if sample_doc_type else False,
        "source_url": len(collection.get(where={"source_url": sample_source}, limit=3).get("ids", [])) > 0 if sample_source else False,
    }

    report = {
        "phase": "2.6",
        "generated_at": iso_now(),
        "input_embeddings_file": "ingestion/phase-2/2.5-embedder/output/embeddings-latest.json",
        "vector_db": "chroma",
        "collection_name": COLLECTION_NAME,
        "persist_directory": "ingestion/phase-2/2.6-indexerr/chroma-data",
        "summary": {
            "total_input_chunks": len(chunks),
            "total_indexed_chunks": total_indexed,
            "embedding_dim": payload.get("embedding_dim"),
        },
        "metadata_filter_validation": filter_checks,
    }

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Indexed chunks into Chroma collection: {COLLECTION_NAME}")
    print(f"Total indexed chunks: {total_indexed}")
    print(f"Wrote index report to: {REPORT_PATH}")


if __name__ == "__main__":
    run()
