# MOSAABAI DEVELOPMENT MODEL v3 — Batched Sprint

## Core Principle
Build in sprints. Audit at sprint boundaries. Fix bugs in batches.

## Sprint Cycle
1. Kickoff: DeepSeek + ChatGPT define scope (2-5 tasks).
2. Build: Grok executes all tasks in one pass.
3. CI: Automatic on push.
4. Audit Gate: Gemini audits actual git objects + CI logs + evidence.
5. Verdict: PASS → merge. F-IDs → Fix Sprint.
6. Next Sprint.

## Fix Sprint
- All F-IDs from a sprint are collected.
- DeepSeek prioritizes P0 vs P1/P2.
- Grok fixes all in one pass.
- Max 2 fix sprints per sprint. Third = redefine scope.

## P0 Security Hotfix Exception
- Confirmed P0 (RCE, sandbox escape, crypto bypass, privilege escalation) fixed immediately.
- Requires Human Director approval.
- NOT for: naming, style, missing tests, design.

## Member Timing
- Human Director: sprint boundaries + P0 hotfixes.
- DeepSeek: continuous during Build Phase.
- ChatGPT: sprint kickoff + post-audit strategic review.
- Grok: Build Phase only.
- Gemini: Audit Phase only (batched, not continuous).

## Anti-Patterns
- Continuous mid-sprint findings.
- Auditing spec text in chat.
- One-by-one F-ID fixing.
- Rejecting sprints for non-blocking issues.

Signed: Human Director (Sole Merge Authority)
Date: 2026-10-05
