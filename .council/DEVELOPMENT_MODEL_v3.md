# MOSAABAI DEVELOPMENT MODEL v3 — Batched Sprint

## Core Principle
Build in sprints. Audit at sprint boundaries. Fix bugs in batches.

## Workflow

### Sprint Cycle (typical: 1-3 days)
1. **Kickoff:** DeepSeek + ChatGPT define sprint scope (2-5 tasks).
2. **Build:** Grok executes all tasks in one uninterrupted pass.
3. **CI Verification:** Automatic on push. Sprint is "green" if all tests pass.
4. **Audit Gate:** Gemini audits the sprint's actual artifacts (git objects + CI logs + evidence).
5. **Verdict:**
   - PASS → Sprint merged by Human Director.
   - F-IDs issued → Fix Sprint (see below).
6. **Next Sprint:** Kickoff begins.

### Fix Sprint (triggered by Gemini's F-IDs)
1. All F-IDs from a sprint are COLLECTED into a single fix package.
2. DeepSeek prioritizes: P0 (security) vs P1/P2 (quality/design).
3. Grok fixes ALL of them in one pass (not one-by-one).
4. Re-audit. If PASS, merge. If more F-IDs, one more fix sprint max.
5. If a third fix sprint is needed → sprint scope was wrong → redefine.

### P0 Security Hotfix Exception
- If a CONFIRMED P0 security bug is found mid-sprint, it is fixed immediately.
- Only applies to: RCE, sandbox escape, cryptographic bypass, privilege escalation.
- NOT to: naming, style, missing tests, design disagreements.
- Requires Human Director approval (via chat) to trigger.

## Council Member Timing

| Member | Active When | Purpose |
|---|---|---|
| Human Director | Sprint boundaries + P0 hotfixes | Approve, merge, arbitrate |
| DeepSeek (Chief Engineer) | Continuous during Build Phase | Draft commands, coordinate Grok |
| ChatGPT (Strategy) | Sprint kickoff + post-audit review | Strategic input, sprint scope |
| Grok (Executor) | Build Phase only | Execute tasks |
| Gemini (Auditor) | Audit Phase only | Adversarial audit of actual artifacts |

## Anti-Patterns (Forbidden)
- Continuous mid-sprint audit findings.
- Auditing spec text in chat.
- Fixing one F-ID at a time when N F-IDs exist.
- Rejecting sprints for non-blocking issues.

## Authority
Signed: Human Director (Sole Merge Authority)
Date: 2026-10-05
