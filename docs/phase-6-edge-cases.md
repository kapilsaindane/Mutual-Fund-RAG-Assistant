# Phase 6 Edge Cases - Minimal UI and User Experience

## Edge Cases
- Disclaimer is hidden on smaller screens.
- Citation link is not clickable or opens malformed URL.
- UI truncates long scheme names and confuses users.
- Refusal and factual responses look identical and reduce clarity.
- Example prompts include advisory language by mistake.

## Handling Strategy
- Keep disclaimer persistent and visible across breakpoints.
- Validate URL rendering and link target sanitization.
- Use responsive text wrapping and scheme name tooltips.
- Apply distinct response styles for factual answer vs refusal.
- Review and lock example prompts to factual-only set.

## Validation Checklist
- Mobile and desktop UI checks pass for disclaimer visibility.
- All rendered citations are valid and open correctly.
- Example questions align with facts-only policy.
