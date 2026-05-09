# Phase 3 Edge Cases - Retrieval Engine (RAG Core)

## Edge Cases
- Retrieval returns semantically similar but wrong scheme.
- Query uses abbreviations (ER, SIP, NAV) and misses relevant chunks.
- Top-k results contain stale facts over newer updates.
- Exact numeric query fails due to lexical mismatch.
- Hybrid ranker over-weights generic FAQ content.

## Handling Strategy
- Apply strict scheme-level metadata filters when scheme is identified.
- Add abbreviation expansion and synonym dictionaries.
- Boost freshness using source date in ranking score.
- Combine lexical and semantic retrieval with weighted fusion.
- Penalize low-specificity chunks and generic boilerplate sections.

## Validation Checklist
- Top-3 retrieval contains correct evidence for benchmark factual queries.
- Scheme confusion rate is tracked and below target.
- Freshness-aware ranking chooses latest valid evidence when available.
