# Query Taxonomy - Phase 0

## Intent Classes

### 1) `FACTUAL_ALLOWED`
Definition: Objective, verifiable questions tied to scheme attributes or documented process.

Examples:
- "What is the expense ratio of HDFC Focused Fund Direct Growth?"
- "What is the lock-in period for HDFC ELSS Tax Saver Fund?"
- "What is the benchmark index of HDFC Large Cap Fund Direct Growth?"

Handling:
- Retrieve evidence from approved URLs.
- Return concise answer under response contract.

---

### 2) `ADVISORY_REFUSE`
Definition: Questions asking for recommendation, suitability, preference, or decision guidance.

Examples:
- "Should I invest in HDFC Mid Cap Fund now?"
- "Which one is better, HDFC Focused or HDFC Equity?"
- "Can you suggest the best fund for me?"

Handling:
- Do not provide recommendation.
- Return refusal template and facts-only boundary.

---

### 3) `PERFORMANCE_RESTRICTED`
Definition: Questions about returns/performance interpretation requiring analysis.

Examples:
- "Will this fund give better returns in 5 years?"
- "Is this fund outperforming others?"

Handling:
- Avoid interpretation or comparison.
- Provide neutral response and one approved citation when possible.

---

### 4) `UNSUPPORTED_REFUSE`
Definition: Out-of-scope questions not covered by approved URL corpus.

Examples:
- "Show me tax rules for a different AMC scheme not in this project."
- "Fetch data from AMFI for all category averages."

Handling:
- Refuse or ask user to reframe within approved project scope.
