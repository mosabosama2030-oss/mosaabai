# EO-005 G4 RE-AUDIT SPECIFICATION — ANCHOR v5.0

## PART 1 — REVISED AC-G4-02 (v6) — Addressing F-061, F-068

AC-G4-02 — Canonical cryptographic identity (REVISION v6)

Every trusted tool MUST possess a deterministic spec_digest.

spec_digest = SHA256(
  canonical_utf8_json({name, description, parameters})
  || bytecode_fingerprint
  || ast_fingerprint
)

bytecode_fingerprint = SHA256(
  fn.__code__.co_code
  || repr(fn.__code__.co_consts)
  || repr(fn.__code__.co_names)
  || repr(fn.__code__.co_varnames)
  || repr(fn.__code__.co_freevars)
  || repr(fn.__code__.co_cellvars)
)

ast_fingerprint = SHA256(ast.dump(ast.parse(inspect.getsource(fn))))

MANDATORY PURITY CONSTRAINTS (F-061):
- co_freevars MUST equal ()
- co_cellvars MUST equal ()
- Tool MUST NOT reference module-level mutable state
- REJECT at registration if violated

MANDATORY AST STATIC ANALYSIS (F-068):
Walk the AST of the tool source. REJECT if any of the following are present:
- ast.Attribute accessing: __globals__, __closure__, __subclasses__, __bases__, __mro__, __class__, __dict__, __code__, __builtins__
- ast.Call targeting: eval, exec, compile, __import__, open, getattr, setattr, delattr, globals, locals, vars, dir, input
- ast.Name with id starting with "__"
- ast.Import or ast.ImportFrom
- ast.Lambda nested inside the tool function

MANDATORY EXECUTION ISOLATION:
- __globals__ replaced with frozen whitelist (arithmetic + comparison builtins ONLY)
- Real module globals inaccessible
- Violation raises SandboxViolation -> HARD CRASH + WAL CRITICAL entry

MANDATORY PROPERTY TESTS (v6):
- Same metadata + same bytecode + same AST -> same digest
- Different bytecode -> different digest
- Different AST (renamed var) -> different digest
- Non-empty co_freevars -> REJECTED at registration
- Tool containing eval() -> REJECTED by AST pass
- Tool accessing __globals__ -> REJECTED by AST pass
- Tool with import statement -> REJECTED by AST pass
- Tool referencing module-level variable -> SandboxViolation at execution

CRITICAL SECURITY RULE:
spec_digest alone MUST NOT authorize an arbitrary caller-supplied object. The registry MUST bind digest to a specific trusted executable instance captured at registration.

---

## PART 2 — CORRECTED EXECUTION ORDER (F-064)

G6a -> G4 -> G4b -> G5 -> G6b -> G8 -> G8b

Rationale:
- G6a (Evidence Infrastructure) MUST be merged to main FIRST.
- No evidence file may be written by ANY task until G6a is live in main.
- G4b writes the first .evidence/EO-005-g4.json UNDER active G6a validation.

---

## PART 3 — OUT-OF-BAND ANCHOR VERIFICATION (F-062)

1. CI step runs: git cat-file -p <COMMIT_SHA>:docs/specs/EO-005_G4_RE_AUDIT_SPEC.md | sha256sum
2. Expected digest stored OUT-OF-BAND by Human Director (NOT in chat, NOT in repo).
3. CI compares computed vs out-of-band value.
4. Failure blocks PR.
5. CI emits signed artifact.
6. Auditor General verifies via CI run output, NOT chat prose.

---

## PART 4 — CI TOKEN INJECTION PROTECTION (F-063)

1. GitHub Environment "audit-signing" MUST be created with Environment Protection Rules.
2. Required reviewers: Human Director + Auditor General (GPG key holder).
3. Secret GEMINI_AUDIT_GPG_KEY scoped to environment only.
4. Token injection runs ONLY on workflow_dispatch with manual approval.
5. pull_request events CANNOT trigger token signing.
6. Grok PRs cannot trigger token signing under any circumstance.

---

## PART 5 — PATH POLICY (F-060)

allowed_paths is STRICT WHITELIST (default-deny).
forbidden_paths is redundant defense-in-depth.

---

## PART 6 — TASK SCHEMA v5.0

{
  "schema_version": "EO-005-tasks-5.0",
  "phase": "EO-005",
  "execution_order": ["G6a", "G4", "G4b", "G5", "G6b", "G8", "G8b"],
  "path_policy": "allowed_paths is STRICT WHITELIST (default-deny). forbidden_paths is redundant.",
  "tasks": [
    {
      "task_id": "G6a",
      "name": "Evidence Infrastructure Setup",
      "dependencies": [],
      "preconditions": ["Current main HEAD confirmed"],
      "allowed_paths": [".github/workflows/evidence-check.yml", "scripts/validate_evidence.py", ".evidence/.gitkeep"],
      "requirements": [
        "Create scripts/validate_evidence.py enforcing schema: base_sha, head_sha, test_result, lint_result, model_id, timestamp",
        "Create .github/workflows/evidence-check.yml (blocking CI)",
        "CI MUST reject PRs without valid .evidence/EO-*.json",
        "EXECUTOR MUST NOT BE GROK (I-026 compliance)",
        "Validator MUST verify Audit_Token signature against Gemini GPG public key",
        "CI MUST include out-of-band anchor verification step per Part 3"
      ],
      "executor": "deepseek",
      "audit_token_required": true
    },
    {
      "task_id": "G4",
      "name": "Canonical Tool Identity Implementation",
      "dependencies": ["G6a"],
      "preconditions": ["G6a merged and CI active"],
      "allowed_paths": ["tools/tool_interface.py", "tools/tool_environment.py", "tools/tool_registry.py", "tests/test_tool_identity.py"],
      "requirements": [
        "Implement AC-G4-02 v6 (bytecode + AST + purity + AST analysis)",
        "All 16 mandatory adversarial tests from Re-Audit Contract",
        "Zero imports of legacy name-based registry in production code",
        "Registry immutability enforced",
        "TOCTOU resistance enforced"
      ],
      "executor": "grok",
      "audit_token_required": true
    },
    {
      "task_id": "G4b",
      "name": "Close G4 with Evidence",
      "dependencies": ["G4"],
      "preconditions": ["G4 passes Gemini re-audit"],
      "allowed_paths": ["tests/test_tool_identity.py", ".evidence/EO-005-g4.json", "docs/EO-005.md"],
      "requirements": [
        "All 16 mandatory tests present and passing",
        "TEST-01 (forged ID), TEST-02 (TOCTOU), TEST-03 (Sandbox), TEST-04 (Memory Poisoning) explicitly required",
        "Update .evidence/EO-005-g4.json with TRUE test/lint results from CI",
        "AUDIT_TOKEN FIELD: Grok MUST leave audit_token field NULL",
        "audit_token will be injected out-of-band by CI (Part 4)",
        "Grok is FORBIDDEN from writing, guessing, or copying Audit_Token",
        "Update status checkboxes in docs/EO-005.md for G4 and G4b"
      ],
      "executor": "grok",
      "audit_token_required": true
    },
    {
      "task_id": "G5",
      "name": "CognitiveLoop Integration",
      "dependencies": ["G4b"],
      "preconditions": ["G4b CLOSED in docs/EO-005.md"],
      "allowed_paths": ["core/cognitive_loop.py", "tests/test_cognitive_loop_integration.py"],
      "requirements": [
        "Loop appends WAL entry before each tool call",
        "All tool calls pass spawn_child() with TrustedToolRegistry binding",
        "ERROR CLASS SEPARATION:",
        "   - Operational (ToolExecutionError, TimeoutError, IOError) -> Result.err(), continue",
        "   - Security (SandboxViolation, SecurityDowngradeError, HashMismatchError, CapabilityViolationError) -> bypass Result, HARD CRASH, halt loop, WAL CRITICAL entry",
        "   - Must use isinstance() checks, NOT broad except Exception",
        "Full 10-stage integration test",
        "Zero imports of legacy ToolRegistry"
      ],
      "executor": "grok",
      "audit_token_required": true
    },
    {
      "task_id": "G6b",
      "name": "Final Evidence Closure Validation",
      "dependencies": ["G5"],
      "preconditions": ["G5 CLOSED"],
      "allowed_paths": [".evidence/"],
      "requirements": [
        "Backfill historical EO closures (G1, G2, G3, G7) into .evidence/",
        "Run validator against ALL evidence files",
        "Verify Audit_Token signatures on all closed EO evidence artifacts",
        "Report closure status",
        "EXECUTOR MUST NOT BE GROK"
      ],
      "executor": "deepseek",
      "audit_token_required": true
    },
    {
      "task_id": "G8",
      "name": "Commit Active EO Status",
      "dependencies": ["G6b"],
      "preconditions": ["G6b CLOSED"],
      "allowed_paths": ["docs/EO-005.md"],
      "requirements": [
        "Update status checkboxes ONLY in docs/EO-005.md",
        "G4, G4b, G5, G6a, G6b marked CLOSED with PR links and SHAs",
        "NO modification to Council roster"
      ],
      "executor": "grok",
      "audit_token_required": true
    },
    {
      "task_id": "G8b",
      "name": "Council Roster Update",
      "dependencies": ["G8"],
      "preconditions": ["G8 CLOSED"],
      "allowed_paths": ["docs/MOSAABAI_MASTER_v1.0.5_FULL.md"],
      "requirements": [
        "Update Council roster with Grok formal membership (execution-only role)",
        "Document: Grok has NO executive, merge, or audit authority",
        "Add Human Director sign-off block",
        "Resolve Master HEAD drift (F-028): update to current main HEAD"
      ],
      "executor": "deepseek",
      "audit_token_required": true
    }
  ]
}

---

## PART 7 — CORRECTIVE COMMIT PLAN FOR MAIN (F-067)

After v5.0 passes Gemini blob audit:
1. Merge spec/EO-005-v5 -> main.
2. Corrective commit replaces docs/specs/EO-005_G4_RE_AUDIT_SPEC.md with v5.0 content.
3. main HEAD moves from 008744f to the new merge commit.
4. v4.0 is preserved in git history but is NOT the governing spec.
