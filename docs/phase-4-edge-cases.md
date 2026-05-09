# Phase 4 Edge Cases - Query Classification and Policy Guardrails

## Edge Cases
- Mixed-intent query: factual + advisory in one prompt.
- Soft advisory phrasing slips through classifier ("Is it safe to invest now?").
- Comparative wording hidden in neutral language ("Which is more suitable?").
- Unsupported queries get answered with fabricated assumptions.
- Refusal text accidentally contains suggestive investment language.

## Handling Strategy
- Split mixed-intent prompts and refuse advisory portion while answering factual part only if safe.
- Add adversarial prompt patterns for soft-advice detection.
- Introduce explicit comparison intent markers.
- Block generation when classifier confidence is low; return safe refusal.
- Validate refusal templates against banned advisory phrase list.

## Validation Checklist
- Advisory leakage tests pass for direct and indirect recommendation prompts.
- Classifier confidence thresholds are calibrated using validation set.
- Refusal responses remain polite, clear, and non-prescriptive.
