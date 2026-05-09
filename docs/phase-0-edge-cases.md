# Phase 0 Edge Cases - Requirement Freeze and Compliance Blueprint

## Edge Cases
- Scope drift: team interprets "official sources" as domain-level only and adds non-approved pages.
- Ambiguous query classes: prompts like "Is this fund good for long term?" are treated as factual.
- Footer inconsistency: date format varies across components.
- Citation ambiguity: responses include multiple links in markdown preview.
- Policy mismatch: business wants comparisons while compliance forbids recommendations.

## Handling Strategy
- Lock policy to exact URL and response contract before build starts.
- Define a strict query taxonomy with examples for allowed and refused intents.
- Standardize footer format to one schema: `Last updated from sources: YYYY-MM-DD`.
- Enforce exactly one URL token at validator level.
- Record policy exceptions as rejected requirements unless compliance approval exists.

## Validation Checklist
- All rules are testable and mapped to unit tests.
- Refusal examples exist for advisory, ranking, and "better/worse" queries.
- Output contract is versioned and signed off by stakeholders.
