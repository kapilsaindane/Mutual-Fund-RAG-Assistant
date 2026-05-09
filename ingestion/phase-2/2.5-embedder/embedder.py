import json
from datetime import datetime, timezone
from pathlib import Path


MODEL_NAME = "BAAI/bge-small-en-v1.5"
ROOT = Path(__file__).resolve().parents[3]
INPUT_PATH = ROOT / "ingestion" / "phase-2" / "2.4-chunker" / "output" / "chunks-latest.json"
OUTPUT_DIR = ROOT / "ingestion" / "phase-2" / "2.5-embedder" / "output"
OUTPUT_PATH = OUTPUT_DIR / "embeddings-latest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. Install it with: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer(MODEL_NAME)


def run() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        chunk_payload = json.load(f)

    chunks = chunk_payload.get("chunks", [])
    texts = [c.get("text", "") for c in chunks if c.get("text")]

    if not texts:
        raise RuntimeError("No valid chunk text found in Phase 2.4 output.")

    model = load_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    vector_lists = vectors.tolist()

    dims = {len(v) for v in vector_lists}
    if len(dims) != 1:
        raise RuntimeError(f"Embedding dimension mismatch detected: {sorted(dims)}")
    embedding_dim = next(iter(dims))

    embedded_chunks = []
    success_count = 0
    for chunk, vector in zip(chunks, vector_lists):
        if not chunk.get("text"):
            continue
        embedded_chunks.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "text": chunk.get("text"),
                "metadata": chunk.get("metadata", {}),
                "embedding": vector,
                "embedding_dim": embedding_dim,
                "embedding_model": MODEL_NAME,
            }
        )
        success_count += 1

    output = {
        "phase": "2.5",
        "generated_at": iso_now(),
        "input_chunks_file": "ingestion/phase-2/2.4-chunker/output/chunks-latest.json",
        "model": MODEL_NAME,
        "embedding_dim": embedding_dim,
        "validation": {
            "dimensional_consistency": True,
            "unique_dimensions_observed": sorted(dims),
        },
        "summary": {
            "total_chunks_input": len(chunks),
            "embedded_success_count": success_count,
            "embedded_failure_count": len(chunks) - success_count,
        },
        "chunks": embedded_chunks,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(output, f)

    print(f"Wrote embeddings output to: {OUTPUT_PATH}")
    print(f"Model: {MODEL_NAME}")
    print(f"Embedding dim: {embedding_dim}")
    print(f"Embedded chunks: {success_count}")


if __name__ == "__main__":
    run()
