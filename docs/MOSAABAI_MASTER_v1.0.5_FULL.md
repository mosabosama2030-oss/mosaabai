# MOSAABAI MASTER DOCUMENT v1.0.5 — FULL
**Status:** FROZEN  
**Date:** 2026-10-05  
**HEAD:** b5079fa3ec7378a74ac3a646ca9cd43f498a8b03  
**Authority:** Human Project Director  
**Steward:** MosaabAI Engineering Council

---

## PART A — COUNCIL CHARTER v2.1.0

### A.1 Council Members

| Role | Owner | Scope |
|------|-------|-------|
| Human Director | (human) | Ultimate authority, merge authority |
| Chairman Emeritus | ChatGPT | Strategic synthesis, constitutional ratification |
| Acting Chairman + Chief Engineer | DeepSeek | Executive orders, contracts, implementation |
| Auditor General | Gemini | Forensic audit, adversarial discovery |
| Security Officer | Claude (future) | Threat modeling |

### A.2 Canonical Workflow

1. Human Director requests → DeepSeek drafts EO
2. Council reviews (ChatGPT + Gemini independently)
3. DeepSeek reconciles verdicts
4. Human Director approves
5. Execution on branch only
6. Both audit
7. Human Director merges

### A.3 Authority Boundaries

- No autonomous agent has merge authority
- All writes require explicit EO authorization
- All EOs produce `.evidence/EO-XXX.json`
- Empty result ≠ success (mark UNKNOWN)

---

## PART B — CONSTITUTIONAL INVARIANTS

| ID | Name | Rule |
|----|------|------|
| I-001 | Sovereign Authority | No model output creates authority |
| I-005 | Monotonic Delegation | E(child) ⊆ E(parent) |
| I-008 | Provenance | Every action attributable |
| I-011 | Resource Boundedness | All resources bounded |
| I-012 | Model Replaceability | Model swap does not change Core |
| I-014 | Verification Requires Evidence | No claim without proof |
| I-020 | No-Payment | Free-tier only |
| I-021 | Provisional Non-Finality | Provisional artifacts tagged |
| I-022 | Quota-Aware Verification | Batch reviews, not real-time |
| I-023 | Cognitive Role Fidelity | Fallbacks role-mapped |
| I-024 | Stagnation Threshold | >120h for paid tier review |
| I-025 | Delegated Role Fidelity | Assistants inherit capability, not authority |
| I-026 | Independent Verification | No self-verification |
| I-027 | Model Identity Pinning | Exact model IDs in artifacts |

---

## PART C — CANONICAL CONTRACTS

### C.1 Error Envelope (core/errors.py)

- `ErrorCode`: 11 architectural failure states
- `MosaabError`: bounded, JSON-safe, silent truncation
- `Result[T]`: monad with is_ok/is_err/unwrap/unwrap_err
- Limits: message ≤1000, context ≤10 keys, value ≤500 chars
- Truncation: silent, marked with `...[TRUNCATED]`, flags in `_truncation_flags`
- Never raises during bounding (AGENTS.md L8)

### C.2 WAL (core/wal.py)

- `IntentStatus`: PENDING, EXECUTING, COMPLETED, FAILED, ROLLED_BACK
- `WALEntry`: entry_id, action_id, idempotency_key, intent, status
- `WriteAheadLog`: JSONL format, thread-safe, compact(max_entries)
- **PENDING G2:** fsync implementation requires os.fsync(fd) fix
- **PENDING G2b:** payload/retention bounds

### C.3 Tool Environment (tools/tool_environment.py)

- `ToolEnvironment`: frozen, per-agent
- `create_root(env_id, tools, capabilities)`: factory
- Monotonic delegation enforced at spawn_child
- **PENDING G4:** canonical tool identity by spec_digest, not name
- **PENDING G4b:** same-name adversarial test

### C.4 Cognitive Loop (core/cognitive_loop.py)

- 10-stage loop: Understand → Model → Plan → Execute → Observe → Evaluate → Replan → Verify → Learn → Answer
- **PENDING G5:** integrate WAL, Errors, ToolEnvironment

---

## PART D — EO-005 GATES

| Gate | Description | Status |
|------|-------------|--------|
| G1 | Master Document full text (this file) | IN PROGRESS |
| G2 | WAL fsync + directory sync + Termux preflight | PENDING |
| G2b | WAL payload/retention bounds (F-003) | PENDING |
| G3 | errors.py silent truncation (F-006) | ✅ CLOSED (PR #9, b5079fa) |
| G4 | Canonical Tool Identity + TrustedToolRegistry (F-002) | PENDING |
| G4b | Same-name substitution adversarial test | PENDING |
| G5 | CognitiveLoop integration | PENDING |
| G6 | .evidence/EO-*.json + P0.5.0-CLOSURE.json (F-004) | PENDING |
| G7 | CI ruff blocking + branch protection (F-005) | ✅ CLOSED (PR #8) |
| G8 | Active EO committed to repository (F-001) | PENDING |

---

## PART E — STATE HISTORY

### Merged PRs

| PR | Description | Commit |
|----|-------------|--------|
| #4 | WAL (A0.1) | c096ae7 |
| #5 | Error Envelope (A0.2) | c4e5a5b |
| #6 | Tool Environment (A0.3) | 65342f0 |
| #7 | EO-004 Integration Suture | 5d92473 |
| #8 | Ruff Preflight | 0f8caab |
| #9 | EO-005 G3 (v1+v2+v3) | b5079fa |

### Forensic Findings Resolved

- F-005: Ruff claim false → PR #8
- F-006: errors.py raised instead of silent truncation → PR #9
- F-007: Result invariants removed → restored in v2
- F-008: JSON-safe coercion → restored in v2
- F-009: Malformed context → hardened in v3
- F-013: Type precision → restored in v3
- F-014: Adversarial tests → added in v3
- F-015: Misrepresentation → resolved in v3

### Metrics

- Tests: 151 (was 138 at baseline)
- Ruff: clean (blocking)
- CI: 2/2 on Python 3.11 + 3.12
- Zero regressions

---

## PART F — CLOSURE STANDARD

A requirement is CLOSED only when:

1. Implementation satisfies exact requirement
2. Tests demonstrate it
3. Adversarial/failure-path tests exist (security/durability)
4. CI enforces gate (blocking)
5. Evidence artifact complete + schema-valid
6. Independent audit (Gemini) PASS
7. Human Director signs off

**Never declare closure without all 7 conditions.**

---

## SIGNATURE

**Ratified by:**
- Human Project Director — PENDING
- ChatGPT (Chairman Emeritus) — PENDING
- DeepSeek (Acting Chairman + Chief Engineer) — SIGNED
- Gemini (Auditor General) — PENDING

---

**END OF MASTER DOCUMENT v1.0.5 — FULL**
