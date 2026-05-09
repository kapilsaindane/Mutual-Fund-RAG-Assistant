# Phase 2 Edge Cases - Data Ingestion, Normalization, and Chunking

## Edge Cases
- PDF extraction fails for scanned or image-heavy content.
- Tables (expense ratio, exit load) lose structure during parsing.
- Duplicate chunks are created from repeated page sections.
- Chunk boundaries split a key fact across two chunks.
- Metadata missing for some chunks (scheme/doc type/source date).

## Handling Strategy
- Use OCR fallback only when extraction confidence is low.
- Add table-aware parser and preserve row/column context in text form.
- Hash chunk text and metadata to detect duplicates.
- Use overlap-based chunking and section-aware splits.
- Reject chunks without mandatory metadata fields.

## Validation Checklist
- Extraction success threshold met for all approved URLs.
- Structured numeric facts remain intact after parsing.
- Duplicate rate and null-metadata rate remain below defined limits.
