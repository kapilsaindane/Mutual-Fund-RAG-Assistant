# Policy Test Checklist - Phase 0 Exit Criteria

## A) Scope and Source Controls
- [ ] System accepts only exact URLs listed in `scope-lock.md`.
- [ ] Non-approved URL is rejected by allowlist validator.
- [ ] Redirected URL is rejected unless exact approved match.

## B) Query Classification
- [ ] Factual query mapped to `FACTUAL_ALLOWED`.
- [ ] Advisory query mapped to `ADVISORY_REFUSE`.
- [ ] Performance query mapped to `PERFORMANCE_RESTRICTED`.
- [ ] Out-of-scope query mapped to `UNSUPPORTED_REFUSE`.

## C) Output Contract
- [ ] Response body never exceeds 3 sentences.
- [ ] Exactly one citation URL is present.
- [ ] Citation URL belongs to approved scope.
- [ ] Footer appears exactly as `Last updated from sources: YYYY-MM-DD`.

## D) Privacy and Safety
- [ ] Sensitive identifiers are not stored.
- [ ] Advisory language does not appear in factual responses.
- [ ] Refusal responses are polite and clear.

## E) Sign-Off
- [ ] Policy specification approved.
- [ ] Response contract approved.
- [ ] Query taxonomy approved.
- [ ] Phase 0 exit criteria marked complete.
