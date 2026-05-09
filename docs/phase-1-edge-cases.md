# Phase 1 Edge Cases - Corpus Curation and Source Governance

## Edge Cases
- One approved URL is unreachable (timeout or temporary outage).
- Same scheme appears with inconsistent naming across pages.
- Non-fund informational text dominates a page and dilutes relevance.
- URL redirects to a new path and fails exact-match allowlist.
- Incomplete coverage: one required scheme has missing critical facts.

## Handling Strategy
- Add retry with backoff and mark temporary failures separately from permanent failures.
- Normalize scheme names through a canonical mapping table.
- Tag and down-rank generic boilerplate sections during ingestion.
- Maintain redirect map, but still require resolved URL to be explicitly approved.
- Flag coverage gaps and block progression until required fields are available.

## Validation Checklist
- All five approved URLs are reachable and categorized.
- Canonical scheme naming is consistent in registry.
- Source registry captures URL, type, scheme, and timestamp for every entry.
