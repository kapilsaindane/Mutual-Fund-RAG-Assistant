# Phase 2.1 Validation Checklist - Fetcher

## Input Gate
- [ ] Input URL list contains exactly 5 approved URLs.
- [ ] Every input URL is present in Phase 1 allowlist.
- [ ] No unapproved URL proceeds to fetch.

## Fetch Execution
- [ ] Fetch attempted for all approved URLs.
- [ ] Retries applied only to transient failures.
- [ ] Fetch process continues when one URL fails.

## Metadata Capture
- [ ] Metadata record exists for each attempted URL.
- [ ] Required fields are complete:
  - `fetch_status`
  - `http_status_code`
  - `fetched_at`
  - `response_fingerprint`
  - `content_type`
  - `content_length`
- [ ] Failure records include `error_message`.

## Exit Check
- [ ] Phase 2.1 outputs are generated and stored.
- [ ] Non-approved URLs were blocked by policy.
- [ ] Phase 2.2 can start using fetch outputs.
