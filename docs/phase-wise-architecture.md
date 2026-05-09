# Phase-Wise Architecture: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## 1) Purpose and Design Principles

This architecture is designed for a Retrieval-Augmented Generation (RAG) assistant that answers only objective, verifiable mutual fund FAQs from official public sources (AMC, AMFI, SEBI).  
The system explicitly avoids advice, recommendations, comparisons, and speculative responses.

Core principles:
- Facts-only responses from curated official documents
- Exactly one citation per answer
- Maximum three sentences per answer
- Mandatory footer: `Last updated from sources: <date>`
- Safe refusal for advisory or out-of-scope questions
- Minimal UI with clear compliance disclaimer

---

## 2) High-Level Architecture Layers

1. **Source Layer**
   - Official URLs from selected AMC + AMFI + SEBI
   - Factsheets, SID, KIM, FAQ/help pages, statement/tax download guides

2. **Ingestion and Processing Layer**
   - URL validation and allowlist enforcement
   - Content extraction, cleaning, chunking, metadata tagging
   - Periodic refresh pipeline

3. **Knowledge and Retrieval Layer**
   - Vector index for semantic retrieval
   - Optional lexical index for keyword precision (e.g., "exit load", "ELSS lock-in")
   - Metadata filters by scheme, document type, and source authority

4. **Guardrails and Policy Layer**
   - Query classifier (factual vs advisory vs unsupported)
   - Refusal template for advisory queries
   - Output validator for sentence limit, single citation, and footer format

5. **Answer Generation Layer**
   - Controlled generation using retrieved evidence only
   - Citation selection policy (single best source)
   - Response formatting policy

6. **Experience Layer**
   - Minimal web/chat interface
   - Welcome message, example questions, disclaimer

7. **Observability and Governance Layer**
   - Logs for query class, source used, refusal reason, latency
   - Source freshness dashboard
   - Audit trail for compliance checks

---

## 3) Phase-Wise Implementation Plan

## Phase 0: Requirement Freeze and Compliance Blueprint

### Goals
- Convert problem statement constraints into testable rules.
- Define non-negotiable compliance boundaries.

### Activities
- Freeze project URL scope to exactly these five URLs (no additional URLs allowed in this project):
  - https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth
  - https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth
  - https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth
- Create policy matrix:
  - Allowed: factual scheme and process queries
  - Refuse: advice, better/worse comparisons, investment suggestions
  - Restrict: performance questions -> factsheet link only
- Define response contract:
  - Max 3 sentences
  - Exactly 1 citation URL
  - Footer with date
- Define sensitive data policy: no PAN/Aadhaar/account/OTP/contact data handling

### Deliverables
- `policy-spec.md`
- `response-contract.md`
- `query-taxonomy.md`

### Exit Criteria
- Policy test checklist approved and mapped to validation rules.

---

## Phase 1: Corpus Curation and Source Governance

### Goals
- Build a high-quality, official-source corpus with controlled scope.

### Activities
- Keep corpus scope locked to the same five approved URLs from Phase 0 only.
- Do not add, replace, or expand URLs beyond the approved five links.
- Build source registry with fields:
  - URL
  - source type (factsheet/SID/KIM/FAQ/AMFI/SEBI/process guide)
  - scheme name
  - authority level
  - retrieval timestamp
  - refresh frequency
- Enforce a strict URL allowlist (exact-match check against the five approved links).

### Deliverables
- `source-registry.csv` or `source-registry.json`
- `allowlist-config.json`

### Exit Criteria
- 100% URLs valid, reachable, official, and categorized.

---

## Phase 2: Data Ingestion, Normalization, and Chunking

### Goals
- Convert raw web/PDF content into reliable retrieval-ready chunks.

### Subphases (implement in order)

#### URLs (Input Gate)
- Use only the five approved URLs from Phase 0/Phase 1 source registry.
- Reject any non-approved URL before ingestion starts.

#### Phase 2.1: Fetcher
- Crawl/fetch content from approved URLs.
- Capture fetch metadata (status, timestamp, response fingerprint).

#### Phase 2.2: Extractor
- Extract raw text from HTML/PDF sources.
- Preserve section structure where available.

#### Phase 2.3: Cleaner
- Normalize text formatting and remove boilerplate/noise.
- Standardize whitespace, symbols, and repeated template fragments.

#### Phase 2.4: Chunker
- Split cleaned HTML-derived text into retrieval-ready chunks with overlap (target 600-900 characters, 120-180 overlap).
- Because current pages still include platform/navigation content, apply a pre-chunk relevance filter to keep fund-fact content and drop residual generic UI text.
- Use section-first chunking when heading quality is good; otherwise fall back to paragraph-window chunking.
- Attach chunk metadata:
  - chunk id
  - source URL
  - source date
  - scheme
  - doc type (currently `html_fund_page`)
  - section heading (fallback to `Document` when unavailable)
  - cleaner version
  - relevance score

#### Phase 2.5: Embedder
- Generate embeddings for each valid chunk.
- Validate embedding creation success and dimensional consistency.

#### Phase 2.6: Indexerr
- Store embedded chunks in retrieval index.
- Ensure metadata filters are indexable (scheme/doc type/source).

#### Phase 2.7: Refresh & Health
- Add scheduled refresh for changed source content using GitHub Actions.
- Implement automated data pipeline with:
  - Daily/weekly scheduled jobs for source updates
  - Change detection and incremental updates
  - Failure notifications and retry mechanisms
- Run quality gates:
  - Empty chunk detection
  - Duplicate chunk detection
  - Broken extraction detection
  - Embedding/index health checks

### Deliverables
- `ingestion-pipeline`
- `normalized-corpus`
- data quality report
- GitHub Actions workflow files for scheduled updates
- CI/CD pipeline configuration

### Exit Criteria
- Minimum 95% extraction success and clean metadata coverage.

---

## Phase 3: Retrieval Engine (RAG Core)

### Goals
- Retrieve precise, high-confidence evidence for factual questions using optimal strategy for small corpus.

### Corpus Analysis
- **Size**: 50 chunks total (small corpus optimized for dense retrieval)
- **Distribution**: 5 schemes, 8-13 chunks each
- **Content**: Structured fund factsheets with numerical data
- **Chunk Quality**: 600-900 chars with section-based chunking

### Optimal Retrieval Strategy

#### 1. Dense-First Hybrid Retrieval
**Primary Strategy**: Dense retrieval as primary (weight: 0.7), Sparse as enhancement (weight: 0.3)
**Rationale**: Small corpus size makes dense retrieval more effective than sparse

#### 2. Adaptive Weighting by Query Type
- **Semantic-heavy queries** (default): Dense=0.7, Sparse=0.3
- **Numeric-heavy queries** (₹, %, digits): Dense=0.4, Sparse=0.6
- **Exact-match queries** (specific values): Dense=0.3, Sparse=0.7

#### 3. Scheme-First Retrieval
```python
if scheme_confidence >= 0.8:
    # Search only scheme-specific chunks (8-13 docs)
    results = dense_search(query, scheme_chunks, top_k=5)
else:
    # Fallback to full corpus search
    results = hybrid_search(query, all_chunks, top_k=10)
```

#### 4. Optimized RRF for Small Corpus
- **Standard RRF**: k=60 → **Small Corpus RRF**: k=20
- **Top-K per Channel**: `min(20, n_candidates)` → `min(10, n_candidates)`
- **Final Results**: Top-3 after cross-encoder re-ranking

#### 5. Section-Based Boosting
Leverage existing chunk structure with targeted boosts:
- "expense ratio" → 1.3x boost
- "exit load" → 1.3x boost  
- "sip" → 1.2x boost
- "nav" → 1.2x boost
- "risk" → 1.2x boost
- "lockin" → 1.3x boost

### Activities
- Build dense-first hybrid retrieval with adaptive weighting
- Implement scheme-aware filtering with confidence thresholds
- Add section-based boosting using existing chunk metadata
- Optimize RRF parameters for 50-chunk corpus
- Implement cross-encoder re-ranking (BAAI/bge-reranker-base)
- Add confidence gate with margin detection for "I don't know" responses
- Create CLI interface and evaluation framework

### Deliverables
- Dense-first hybrid retriever with adaptive weights
- Scheme-aware filtering system
- Cross-encoder re-ranker with confidence analysis
- CLI interface (`python retrieval/phase-3/cli.py "query"`)
- 30-question evaluation framework
- Retrieval service API (`/retrieve`)

### Exit Criteria
- Top-1 chunk contains gold answer for ≥85% of 30-question eval set
- Success rate measured across easy/medium/hard query types
- Confidence gate prevents low-confidence responses

---

## Phase 4: Query Classification and Policy Guardrails

### Goals
- Prevent advisory output and enforce facts-only behavior.

### Activities
- Build query intent classifier:
  - `FACTUAL_ALLOWED`
  - `ADVISORY_REFUSE`
  - `UNSUPPORTED_REFUSE`
- Rule examples:
  - "Should I invest..." -> `ADVISORY_REFUSE`
  - "Which fund is better..." -> `ADVISORY_REFUSE`
  - "What is expense ratio..." -> `FACTUAL_ALLOWED`
- Configure refusal responses:
  - polite refusal
  - one educational link (AMFI/SEBI)
  - no recommendation language

### Deliverables
- guardrail service (`/classify-query`)
- refusal template library
- policy unit tests

### Exit Criteria
- Advisory leakage rate approximately zero in test suite.

### Implementation Details

#### Query Intent Classifier
- **Pattern-based classification** using regex for advisory/comparison/prediction detection
- **Intent types**: FACTUAL_ALLOWED, ADVISORY_REFUSE, COMPARISON_REFUSE, PREDICTION_REFUSE, UNSUPPORTED_REFUSE
- **Confidence scoring** based on pattern matches and query features
- **Fallback behavior** to factual when no clear refusals detected

#### PII Detection System
- **PII types**: PAN, Aadhaar, email, phone, OTP, account numbers, bank details
- **High confidence detection** for standard formats (PAN: ABCDE1234F)
- **Medium confidence detection** for ambiguous patterns (10-digit numbers)
- **Redaction capability** for logging with *** masking

#### Refusal Composer
- **Educational URLs**: AMFI/SEBI for all refusal types
- **Template selection** based on confidence level and context
- **Policy-compliant language** with no advisory terms
- **"I don't know" templates** with scheme hints
- **URL Policy**: Zero URLs for all refusal types including "don't know" responses

#### Policy Enforcer
- **Whitelist enforcement** from sources registry
- **URL policy**: Exactly one whitelisted URL for factual answers
- **Zero URLs** for PII blocks and insufficient evidence responses
- **Scheme mapping** from registry to official URLs

#### Answer Generation Stack

**Extractive Generator (Default)**
- **≤3 sentences** from top reranked chunk
- **URL stripping** to prevent accidental link inclusion
- **Banned token detection** for advisory language
- **Source URL and footer** from chunk metadata

**Groq Generator (Optional)**
- **OpenAI-compatible API** via Groq with llama3-8b-8192 model
- **Low temperature** (0.1) for consistent output
- **System prompts** for factual-only behavior
- **Fallback** to extractive on API failure

#### Post-Processor
- **Deterministic checks** for URL count and sentence limits
- **Banned token validation** in final output
- **Footer validation** for required "Last updated" format
- **Safe template fallback** with educational AMFI/SEBI URL

#### Complete Orchestrator
- **Decision flow**: PII → Intent → Retrieval → Generation → Post-processing
- **Automatic method selection** (Groq when available, extractive fallback)
- **Comprehensive logging** and error handling
- **Interactive mode** with help system

### Exit Criteria
- 100% of generated answers respect URL policy above on eval set
- 0 hallucinated or extra URLs on factual paths
- All responses meet format requirements (≤3 sentences, 1 URL, footer)

---

## Phase 5: Controlled Answer Generation and Formatting

### Goals
- Generate concise, evidence-grounded output that strictly follows response format.

### Activities
- Implement generation template:
  - use retrieved facts only
  - no inferred advice
  - max 3 sentences
  - exactly 1 citation URL
  - append footer with last updated date from selected source
- Build output validator:
  - sentence count validator
  - single-link validator
  - banned phrase detector (advice-oriented language)
  - footer schema validator
- If validator fails, auto-rewrite response using stricter template.

### Deliverables
- answer service (`/answer`)
- response validator
- fallback formatter

### Exit Criteria
- 100% responses in validation set meet formatting and citation contract.

---

## Phase 6: Minimal UI and User Experience

### Goals
- Deliver a clean, low-friction interface for facts-only Q&A.

### Activities
- Build minimal UI with:
  - welcome message
  - 3 example factual questions
  - persistent disclaimer: `Facts-only. No investment advice.`
- Render response with:
  - answer text
  - single source link
  - footer date
- Handle refusal responses with consistent tone and educational link.

### Deliverables
- frontend page (web UI/chat panel)
- UX copy for examples and disclaimer

### Exit Criteria
- UI complete and all output states (answer/refusal/error) validated.

---

## Phase 7: Security, Privacy, and Compliance Hardening

### Goals
- Ensure system operation remains safe and compliant.

### Activities
- Input redaction for accidental sensitive data in user queries.
- Disable storage of user-identifiable sensitive fields.
- Configure logging minimization and retention policy.
- Add domain-level egress controls to prevent non-allowlisted fetches.
- Add compliance regression tests for banned behaviors.

### Deliverables
- privacy controls
- secure logging config
- compliance test report

### Exit Criteria
- No restricted data stored; all compliance tests passing.

---

## Phase 8: Evaluation, UAT, and Launch Readiness

### Goals
- Validate factual accuracy, refusal correctness, and operational stability.

### Activities
- Build evaluation suite:
  - factual Q&A set
  - adversarial advisory prompts
  - ambiguous and edge-case prompts
- Track metrics:
  - factual accuracy
  - citation validity
  - refusal precision/recall
  - response latency
  - source freshness SLA compliance
- Run user acceptance test with support/content stakeholders.

### Deliverables
- evaluation report
- UAT sign-off
- go-live checklist

### Exit Criteria
- Success criteria from problem statement are demonstrably met.

---

## Phase 9: Production Operations and Continuous Improvement

### Goals
- Keep answers current, reliable, and policy-compliant after launch.

### Activities
- Schedule source refresh jobs using GitHub Actions (daily/weekly by document type).
- Implement automated CI/CD pipeline with:
  - Scheduled workflows for data ingestion
  - Change detection and incremental updates
  - Automated testing and validation
  - Deployment triggers for successful updates
- Re-index changed documents and invalidate stale chunks.
- Monitor failed fetches and broken source URLs.
- Run periodic policy drift tests against new prompt patterns.
- Maintain changelog for source updates and model/prompt revisions.

### Deliverables
- monitoring dashboard
- incident playbook
- monthly quality review report
- GitHub Actions production workflows
- automated deployment and rollback scripts

### Exit Criteria
- Stable operations with measurable quality over time.

---

## 4) End-to-End Request Flow

1. User submits question in UI.
2. Query classifier labels intent.
3. If advisory/unsupported -> refusal template with educational link.
4. If factual -> retrieval service fetches top evidence chunks.
5. Generator composes concise answer from evidence.
6. Output validator enforces:
   - <= 3 sentences
   - exactly 1 citation
   - footer date format
7. UI displays response and metadata.
8. System logs non-sensitive telemetry for audit and monitoring.

---

## 5) Suggested Component Breakdown

- **Frontend**
  - Query input, examples, disclaimer, response rendering
- **API Gateway**
  - Request routing, auth (if needed), rate limiting
- **Policy Engine**
  - Query classification + refusal decisioning
- **Retriever**
  - Hybrid search over curated corpus
- **Answer Composer**
  - Evidence-grounded response generation
- **Response Validator**
  - Structural and policy checks before returning output
- **Ingestion Worker**
  - Crawl/extract/normalize/index refresh jobs
- **Metadata Store**
  - Source registry, timestamps, scheme/doc mappings
- **Observability Stack**
  - Logs, metrics, alerting, compliance dashboards
- **GitHub Actions Scheduler**
  - Automated data refresh workflows
  - CI/CD pipeline for deployments
  - Change detection and incremental updates

---

## 6) Quality Gates by Phase

- **Source Gate:** only allowlisted official domains pass.
- **Data Gate:** chunk quality and metadata completeness verified.
- **Retrieval Gate:** benchmark recall threshold met.
- **Policy Gate:** advisory refusal tests pass.
- **Output Gate:** response contract validation is 100% pass.
- **Release Gate:** UAT sign-off + monitoring and rollback readiness.

---

## 7) Risk Register and Mitigations

- **Risk:** Outdated factsheets cause stale answers.  
  **Mitigation:** freshness SLA, scheduled refresh, last-updated footer.

- **Risk:** Advisory leakage from model behavior.  
  **Mitigation:** intent classifier + banned phrase checks + strict refusal templates.

- **Risk:** Incorrect source linking.  
  **Mitigation:** enforce citation from retrieved evidence only; validate URL ownership.

- **Risk:** Ambiguous query without scheme context.  
  **Mitigation:** ask a neutral clarification question before answering.

- **Risk:** Parsing failures on PDF format changes.  
  **Mitigation:** extraction health checks and fallback parser pipeline.

---

## 8) Definition of Done (Project Level)

The solution is considered complete when:
- It reliably answers factual mutual fund FAQs from official sources.
- It refuses advisory and comparative recommendation queries.
- Every response includes one valid source link and last-updated footer.
- Response length and style constraints are always enforced.
- The UI is minimal, clean, and includes the compliance disclaimer.
- Monitoring, source refresh, and compliance regression checks are operational.
- GitHub Actions workflows are configured for automated data updates and deployments.
- Scheduled jobs ensure data freshness with proper error handling and notifications.

