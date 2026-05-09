# Phase 2.1 - Fetcher Specification

## Objective
Fetch content from approved URLs only and capture required fetch metadata for downstream extraction.

## Inputs
- URL list from `phase-2.1-input-urls.json`
- Allowlist from `../phase-1/allowlist-config.json`
- Source metadata from `../phase-1/source-registry.json`

## Functional Requirements
1. Accept only URLs in approved input list.
2. Validate URL against exact-match allowlist before request.
3. Fetch page content over HTTPS.
4. Capture fetch metadata for each URL:
   - status
   - timestamp
   - response fingerprint
5. Record fetch result as success/failure with reason.

## Fetch Metadata Fields
- `url`
- `fetch_status` (`success` | `failure`)
- `http_status_code`
- `fetched_at`
- `response_fingerprint` (for change detection)
- `content_type`
- `content_length`
- `error_message` (nullable)

## Non-Functional Requirements
- Deterministic behavior for same URL set and same network state.
- No scope expansion during fetch.
- Retry policy: up to 2 retries for transient failures.

## Failure Handling
- Non-approved URL: reject and log as policy failure.
- Timeout/network issue: retry then mark failure.
- Non-200 status: mark failure and continue processing remaining URLs.

## Output
- A fetch run record using `phase-2.1-fetch-run-template.json`.
- Raw content snapshots (path to be defined in implementation stage).

## Exit Criteria for Phase 2.1
- All input URLs are validated against allowlist.
- Fetch metadata exists for every attempted URL.
- Failures are captured without replacing URLs.
