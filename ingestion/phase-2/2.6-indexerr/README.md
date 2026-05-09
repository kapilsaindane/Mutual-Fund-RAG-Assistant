# Phase 2.6 - Indexerr

Stores embedded chunks in a persistent ChromaDB collection and validates metadata filterability.

## Run
```bash
python ingestion/phase-2/2.6-indexerr/indexerr.py
```

## Input
- `ingestion/phase-2/2.5-embedder/output/embeddings-latest.json`

## Output
- Chroma persistent directory: `ingestion/phase-2/2.6-indexerr/chroma-data/`
- Index run report: `ingestion/phase-2/2.6-indexerr/output/index-report-latest.json`
