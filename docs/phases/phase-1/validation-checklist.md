# Phase 1 Validation Checklist

## Exit Criteria Validation
- [ ] Exactly five URLs exist in `source-registry.json`.
- [ ] `source-registry.json` includes required fields for each source:
  - URL
  - source type
  - scheme name
  - authority level
  - retrieval timestamp
  - refresh frequency
- [ ] `allowlist-config.json` mode is `exact_url_match`.
- [ ] No non-approved URLs are present in allowlist.
- [ ] Corpus scope remains locked to Phase 0 approved URLs only.
- [ ] URL reachability and categorization review completed by implementation owner.

## Notes
- If any URL is unreachable during runtime, do not replace with a new URL.
- Any scope change requires explicit update to Phase 0 scope lock before Phase 1 files can be modified.
