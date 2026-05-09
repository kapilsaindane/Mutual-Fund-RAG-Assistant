# Phase 3 - Retrieval Layer

## Purpose

Given a user query, surface the minimum set of chunks needed to answer factually using hybrid retrieval with cross-encoder re-ranking.

## Pipeline Architecture

```
Query
  │
  ├─► Query Normalizer  (NFKC, lowercase, collapse whitespace; MF tokens like ELSS/SIP/NAV/AUM)
  │
  ├─► Scheme Resolver   (NER-lite: longest substring match on scheme name + aliases from sources.yaml)
  │
  ├─► Hybrid Retriever
  │     ├─ Dense (same HF model as Phase 1.5; query = normalized text, or scheme_name then blank line then query when resolver hits — aligns with chunk embedding shape)
  │     └─ Sparse (BM25, same tokenization as Phase 1.6 index)
  │     → Weighted Reciprocal Rank Fusion → fused top‑10
  │       • Default equal weights; **numeric-heavy** queries (digits / ``₹`` / ``%``) bump sparse weight vs dense (exact facts).
  │       • **Small corpus (~35 chunks):** effective ``top_k`` per channel is ``min(20, n_candidates)`` after optional scheme filter.
  │
  ├─► Optional section hint — light score boost when query keywords match a chunk's ``section`` (e.g. "exit load" → *Exit Load and Tax*).
  │
  ├─► Cross-encoder Re-ranker  (default: ``BAAI/bge-reranker-base``) → top‑3 passages
  │
  └─► Confidence Gate   — low confidence when rerank margin (top − 2nd) is tiny → "I don't know" path (Phase 3)
```

## Why hybrid + rerank?

Mutual fund queries mix exact tokens (e.g., "0.45%", "1 year", "₹500") with semantic phrasing ("how long is the lock-in?"). BM25 nails exact, dense nails semantic; cross-encoder picks the best chunk.

## Filters Applied Before Retrieval

- `scheme_id = <resolved scheme>` → intersect hybrid candidate lists with chunks for that scheme only
- If that filters out all candidates, relax scheme filter once and search the full corpus
- `doc_type = Product_Page` (only doc type in corpus for this iteration)

## Implementation

### Module Structure
```
retrieval/phase-3/
├── __init__.py              # Module exports
├── README.md                # This file
├── query_normalizer.py       # Query normalization (NFKC, MF tokens)
├── scheme_resolver.py        # NER-lite scheme resolution
├── hybrid_retriever.py      # Dense + Sparse retrieval with RRF
├── cross_encoder_reranker.py # Cross-encoder re-ranking
├── cli.py                  # Command-line interface
└── evaluation.py            # Evaluation framework
```

### Usage

#### Basic CLI Usage
```bash
# Single query
python retrieval/phase-3/cli.py "What is the expense ratio of HDFC Mid Cap Fund?"

# With options
python retrieval/phase-3/cli.py "ELSS lock-in period" --top-k 5 --show-intermediate

# Interactive mode
python retrieval/phase-3/cli.py --interactive

# JSON output
python retrieval/phase-3/cli.py "NAV details" --output-format json
```

#### Programmatic Usage
```python
from retrieval.phase_3 import HybridRetriever, CrossEncoderReranker, ConfidenceGate

# Initialize components
retriever = HybridRetriever()
reranker = CrossEncoderReranker()
confidence_gate = ConfidenceGate()

# Retrieve and re-rank
query = "What is the expense ratio of HDFC Mid Cap Fund?"
results = retriever.retrieve(query, top_k=10)
reranked_docs, confidence_info = reranker.rerank_with_confidence(results['retrieved_docs'])
gate_decision = confidence_gate.evaluate_confidence(reranked_docs, confidence_info)
```

#### Evaluation
```bash
# Run full evaluation (30 questions)
python retrieval/phase-3/evaluation.py

# With custom output file
python retrieval/phase-3/evaluation.py --output custom-eval.json

# Analyze failures in detail
python retrieval/phase-3/evaluation.py --analyze-failures
```

## Dependencies

### Required Packages
- `sentence-transformers` - For dense retrieval and cross-encoder
- `chromadb` - Vector database access
- `rank-bm25` - Sparse retrieval (BM25)
- `numpy` - Numerical computations
- `pathlib` - Path handling
- `argparse` - CLI argument parsing

### Installation
```bash
pip install sentence-transformers chromadb rank-bm25 numpy
```

## Configuration

### Model Settings
- **Dense Model**: `BAAI/bge-small-en-v1.5` (same as Phase 1.5)
- **Cross-Encoder**: `BAAI/bge-reranker-base` (default)
- **Embedding Dimension**: 384 (from embeddings file)

### Retrieval Parameters
- **Default Weights**: Dense=0.5, Sparse=0.5
- **Numeric-heavy Queries**: Sparse weight bumped to 0.7
- **RRF Parameter**: k=60 (standard)
- **Top-K per Channel**: `min(20, n_candidates)`
- **Final Results**: Top-3 after re-ranking

### Confidence Thresholds
- **Base Confidence**: 0.1
- **Margin Threshold**: 0.05
- **Adaptive Adjustment**: Based on query features

## Performance Characteristics

### Query Types Handled
- **Exact Facts**: "0.45% expense ratio", "₹500 minimum SIP"
- **Semantic Queries**: "how long is the lock-in period?"
- **Scheme-Specific**: "HDFC Mid Cap Fund details"
- **Comparative**: "which fund has lowest expense ratio?"

### Retrieval Strategy
- **BM25**: Excels at exact token matching (numbers, percentages)
- **Dense**: Captures semantic similarity and context
- **Cross-Encoder**: Provides final precision boost
- **Confidence Gate**: Prevents low-confidence responses

## Exit Criteria

Top-1 chunk contains the gold answer for ≥ 85% of a 30-question eval set.

### Evaluation Metrics
- **Success Rate**: Percentage of queries with confident retrieval
- **Scheme Accuracy**: Correct scheme resolution rate
- **Keyword Coverage**: Expected keywords found in top result
- **Confidence Adequacy**: Gate passes for relevant results

### Test Set Coverage
- **Easy Questions**: Basic scheme information (12 questions)
- **Medium Questions**: Specific data points and calculations (12 questions)  
- **Hard Questions**: Comparative and edge cases (6 questions)
- **Scheme Distribution**: Balanced across all 5 HDFC schemes
