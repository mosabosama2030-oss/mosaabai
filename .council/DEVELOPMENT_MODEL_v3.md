# MOSAABAI DEVELOPMENT MODEL v3 — Batched Sprint

## Core Principle
Build in sprints. Audit at sprint boundaries. Fix bugs in batches.

## Workflow

### Sprint Cycle
1. Kickoff: DeepSeek + ChatGPT define sprint scope (2-5 tasks).
2. Build: Grok executes all tasks in one uninterrupted pass.
3. CI Verification: Automatic on push.
4. Audit Gate: Gemini audits actual artifacts (git objects + CI logs + evidence).
5. Verdict: PASS -> merge. F-IDs -> Fix Sprint.
6. Next Sprint begins.

### Fix Sprint
1. All F-IDs from a sprint are COLLECTED into one fix package.
2. DeepSeek prioritizes P0 vs P1/P2.
3. Grok fixes ALL in one pass.
4. Re-audit. If PASS, merge. Max two fix sprints per feature.
5. If third needed -> sprint scope was wrong -> redefine.

### P0 Security Hotfix Exception
- CONFIRMED P0 bugs (RCE, sandbox escape, crypto bypass, privilege escalation) are fixed immediately.
- Requires Human Director approval to trigger.
- Does NOT apply to naming, style, missing tests, or design disagreements.

## Council Member Timing

| Member | Active When | Purpose |
|--------|-------------|---------|
| Human Director | Sprint boundaries + P0 hotfixes | Approve, merge, arbitrate |
| DeepSeek (Chief Engineer) | Continuous during Build | Draft commands, coordinate Grok |
| ChatGPT (Strategy) | Kickoff + post-audit | Strategic input, sprint scope |
| Grok (Executor) | Build Phase only | Execute tasks |
| Gemini (Auditor) | Audit Phase only | Adversarial audit of actual artifacts |

## Anti-Patterns (Forbidden)
- Continuous mid-sprint audit findings.
- Auditing spec text in chat.
- Fixing one F-ID at a time when N exist.
- Rejecting sprints for non-blocking issues.

## Authority
Signed: Human Director (Sole Merge Authority)
Date: 2026-10-05
