# Phase 2.5 - Embedder

Generates embeddings for Phase 2.4 chunks and validates embedding success and dimensional consistency.

## Model
- `BAAI/bge-small-en-v1.5`

## Run
```bash
python ingestion/phase-2/2.5-embedder/embedder.py
```

## Input
- `ingestion/phase-2/2.4-chunker/output/chunks-latest.json`

## Output
- `ingestion/phase-2/2.5-embedder/output/embeddings-latest.json`
