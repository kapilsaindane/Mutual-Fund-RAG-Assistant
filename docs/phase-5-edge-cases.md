# Phase 5 Edge Cases - Controlled Answer Generation and Formatting

## Edge Cases
- Response exceeds three sentences for complex process questions.
- Model emits two or more source links.
- Footer date missing or not mapped to cited source.
- Answer includes hallucinated details not present in retrieved chunks.
- Numeric values are rounded or transformed incorrectly.

## Handling Strategy
- Apply deterministic post-processor to enforce sentence limit.
- Use strict single-citation validator and auto-rewrite on failure.
- Compute footer date directly from cited source metadata.
- Require evidence alignment checks before final response.
- Preserve numeric values exactly as in source text where possible.

## Validation Checklist
- 100% format compliance in test set (sentences, citation, footer).
- Hallucination rate monitored with manual spot checks.
- Numeric fidelity tests pass for expense ratio, SIP, lock-in, and exit load.
