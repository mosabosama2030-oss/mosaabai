# EO-DRIVER-MIND-001 — Proposed Executive Order

**Status:** PROPOSED — AWAITING HUMAN DIRECTOR APPROVAL  
**Task ID:** EO-DRIVER-MIND-001  
**Base SHA:** 9c094cbbd865db4305d4b0defc781d5e3df5b344  
**Target branch:** feat/eo-driver-mind-001  
**Target base:** main  
**Authority:** Human Director — sole merge authority  
**Runtime:** Python 3.11+  
**Dependencies:** Python standard library only; no new third-party dependencies.

## 1. Mission

Implement DriverMind V1 as a deterministic, local-first ride-hailing driver profitability assistant for Uber and DiDi operations in Greater Cairo. It must optimize verified shift take-home, not ride count or displayed fare/km, and must preserve human control over all ride decisions.

## 2. Exact allowed paths

The following paths alone are authorized if this EO is approved:

- `agents/driver_mind/**`
- `cli/driver_mind.py`
- `tests/test_driver_mind/**`
- `docs/driver_mind/DRIVER_MIND_SPEC_AR.md`
- `docs/driver_mind/DRIVER_MIND_RUNBOOK_AR.md`
- `docs/driver_mind/DRIVER_MIND_FINANCIAL_MODEL_AR.md`
- `.evidence/EO-DRIVER-MIND-001.json`

No other path may be created, modified, or deleted under this EO. In particular, `main`, governance documents, `pyproject.toml`, `.github/workflows/**`, the cognitive core, tool runtime, and existing platform integrations are excluded.

## 3. Scope

1. Immutable validated domain models using `Decimal` for all monetary calculations.
2. Driver profile and operating-cost accounting, with provenance and historical snapshots.
3. Uber/DiDi fare normalization with explicit NET/GROSS/UNKNOWN handling.
4. Per-ride and milestone bonus tracking without premature or duplicate recognition.
5. Full-cycle ride evaluation including pickup, trip, post-drop waiting, and repositioning.
6. Shift progress, target gap, overtime economics, and close/reconciliation.
7. Historical zone aggregation with explicit sample sufficiency and UNKNOWN states.
8. SQLite persistence, schema versioning, transactions, idempotency, CSV import/export, backup/restore.
9. Deterministic service facade and Arabic CLI.
10. Arabic specification, financial model, and runbook.
11. Evidence artifact conforming to the repository's actual evidence schema.

## 4. Explicit exclusions

- No LLM arithmetic or authority to override deterministic calculations.
- No Uber/DiDi scraping, reverse engineering, credentials, tokens, or private account access.
- No accessibility automation, simulated clicks, auto-acceptance, or auto-cancellation.
- No paid APIs, services, or new dependencies.
- No unverified live traffic/demand predictions.
- No dashboard or web UI in V1.
- No MosaabAI cognitive-loop or tool-dispatch integration until a separately authorized and verified execution path exists.
- No changes to governance files, `pyproject.toml`, CI workflows, or branch protection.
- No direct commits to `main`; no PR merge.

## 5. Required financial invariants

- Use `Decimal` and a documented rounding policy.
- Never subtract platform commission twice.
- Never count unearned milestone bonuses as realized income.
- Actual fuel receipts override estimated fuel costs.
- Allocate weekly costs using a configurable workday count; six days is only a labeled initial assumption.
- Preserve closed-shift assumptions when the profile changes.
- Unknown fare basis must produce explicit scenarios and block unqualified accept/reject advice.
- Incomplete maintenance data must be disclosed; report known-expense take-home, not complete accounting profit.
- Personal expenses belong in shift reconciliation, not ride marginal contribution.
- Do not convert missing inputs to zero.

## 6. Acceptance criteria

All acceptance criteria in the Human Director's DriverMind Engineering Execution Specification are binding, including all 34 mandatory test vectors. Additionally:

- Existing repository tests must pass without regression.
- Ruff must pass on every changed Python file.
- SQLite data must survive a process restart.
- CSV import must validate rows and prevent duplicates.
- Closed shifts must be immutable to further revenue/expense accumulation.
- No passenger personal data or unnecessary GPS traces may be stored.
- The CLI must report unknowns and assumptions clearly in Arabic.
- Evidence JSON must validate against the repository's actual schema; `audit_token` remains null unless a genuine authorized audit signature exists.
- PR must remain unmerged for Human Director review.

## 7. Verification protocol

Before implementation:
1. Record current branch, clean/dirty state, and recent commit history.
2. Run the repository baseline `pytest -v` and baseline Ruff command.
3. If baseline tests fail, stop and report the actual failures.

During implementation:
1. Work only within allowed paths.
2. Add tests before or alongside each behavior.
3. Run Ruff on each changed Python file.
4. Run focused tests after each sprint.

Before delivery:
1. Run full `pytest -v`.
2. Run Ruff on all changed Python files.
3. Verify persistence across process restart, reconciliation, import/export, and negative/security cases.
4. Validate evidence against the repository schema.
5. Push branch and open a PR to `main`.
6. Stop. Do not merge.

## 8. Sprint boundaries

- Sprint 0: baseline verification and authorization.
- Sprint 1: models, economics, fare normalization.
- Sprint 2: promotions and ride evaluator.
- Sprint 3: shift engine and zone intelligence.
- Sprint 4: SQLite repositories and service facade.
- Sprint 5: CLI and Arabic documentation.
- Sprint 6: full verification, evidence, PR.

## 9. Governance

This file is a proposal only. It does not authorize implementation until the Human Director explicitly approves EO-DRIVER-MIND-001. EO-005 remains active and unchanged. Any scope expansion requires a separate EO amendment and approval.

**Approval state:** PENDING HUMAN DIRECTOR  
**Merge authority:** Human Director only
