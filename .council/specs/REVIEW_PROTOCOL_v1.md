# COUNCIL REVIEW PROTOCOL v1
Applies to: ChatGPT (Strategic + Pre-Forensic), Gemini (Forensic)
Authority: Human Director

## Mandatory Standards for Every Review

### 1. Evidence Tiers (MANDATORY)
Every claim must be tagged:
- VERIFIED: I read the exact bytes at <blob_sha>:<line_numbers>
- INFERRED: Derived from verified facts, but not directly observed
- UNKNOWN: Cannot determine from available artifacts
- CONTRADICTED: Evidence conflicts with an earlier claim

No untagged claims. No "probably" without an INFERRED tag.

### 2. File:Line Citations (MANDATORY)
Every finding MUST cite: <file>:<line_start>-<line_end> and the blob SHA.
Without this, the finding is INVALID.

### 3. PoC Requirement (MANDATORY for Security Claims)
For any P0/P1 security claim, provide executable Python code (10-40 lines)
that demonstrates the vulnerability against the actual code. Not pseudocode.
If a PoC cannot be written, downgrade the claim to INFERRED and explain why.

### 4. Assertion Quality Audit (MANDATORY for Tests)
For each test file under review:
- List each test name
- Confirm it has a meaningful assertion (not just `assert True`)
- Identify assertions that would pass even if the code under test were broken
- Flag missing negative cases (tests that should fail but aren't checked)

### 5. Comparison Against Committed Specs (MANDATORY)
Every claim of "spec compliant" or "spec violation" MUST be compared against
a committed file with its blob SHA. Chat-only specs are INVALID for this purpose.

### 6. No New F-IDs Without Evidence
F-IDs require: file:line + blob SHA + (PoC or assertion analysis).
Otherwise they are "OBSERVATIONS", not findings.

## Anti-Patterns (Forbidden)
- Summarizing code without reading it
- Reporting "20/20" without checking CI logs for the actual count
- Claiming "sandbox exists" without verifying it's actually bound to execution
- Accepting a spec that only exists in chat
- Issuing PASS without a PoC of at least one attack vector
