# Phase 7 Edge Cases - Security, Privacy, and Compliance Hardening

## Edge Cases
- User enters PAN/Aadhaar/account number in free text.
- Logs accidentally store sensitive content in debug mode.
- Non-allowlisted outbound fetch is triggered by malformed citation.
- Prompt injection attempts to bypass policy rules.
- Retention policy keeps raw query text longer than expected.

## Handling Strategy
- Add input redaction and masking before processing/logging.
- Disable verbose payload logging in production.
- Enforce outbound network restrictions and exact URL allowlist checks.
- Use policy-first middleware that cannot be bypassed by prompt text.
- Implement TTL-based log retention and periodic deletion jobs.

## Validation Checklist
- Sensitive pattern detection tests pass for all restricted identifiers.
- Security scan confirms outbound requests only to approved URLs.
- Compliance audit confirms retention and masking controls.
