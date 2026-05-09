# Response Contract - Output Format Standard

## Mandatory Output Rules
- Maximum length: 3 sentences in answer body.
- Citation count: exactly 1 URL.
- Citation validity: URL must be in approved scope.
- Footer required: `Last updated from sources: <date>`.

## Date Format
- Use `YYYY-MM-DD`.
- Date must be derived from source metadata for the cited URL.

## Response Templates

### Factual Answer Template
1) Concise factual answer from approved source evidence.  
2) Optional second sentence for clarifying objective details.  
3) Optional third sentence if needed for completeness.  
Citation: one approved URL  
Footer: `Last updated from sources: YYYY-MM-DD`

### Refusal Template
- Polite refusal sentence with facts-only limitation.
- Optional sentence directing user to ask factual queries.
- Include one educational or policy-safe URL (if configured).
- Footer included in same standard format.

## Validation Rules
- Sentence counter enforces max 3.
- URL parser enforces exactly one hyperlink token.
- Allowlist validator enforces exact URL match.
- Footer validator enforces prefix text and date format.
