# EO-005 G4 RE-AUDIT SPECIFICATION — ANCHOR v4.0

## PART 1 — REVISED AC-G4-02 (Addressing F-059)

AC-G4-02 — Canonical cryptographic identity (REVISED)

Every trusted tool MUST possess a deterministic spec_digest.

The digest MUST be computed as:

spec_digest = SHA256(
  canonical_utf8_json({
    "name": <tool.name>,
    "description": <tool.description>,
    "parameters": <tool.parameters>
  })
  || <bytecode_fingerprint>
)

Where bytecode_fingerprint is defined as the SHA256 of:

bytecode_fingerprint = SHA256(
  fn.__code__.co_code
  || repr(fn.__code__.co_consts)
  || repr(fn.__code__.co_names)
  || repr(fn.__code__.co_varnames)
)

If the callable is not a pure Python function (e.g., bound method, callable object, C-extension), the implementation MUST fall back to:

AST_dump(ast.parse(inspect.getsource(callable)))

If neither fn.__code__ nor inspect.getsource() is available, the tool MUST be REJECTED. It cannot be trusted.

The canonical representation MUST be deterministic and MUST be tested. At minimum it MUST cover:
- tool identity metadata (name, description, parameters)
- executable bytecode fingerprint

MUST NOT use:
- tool.name, id(tool), object address, Python hash(), registration order

MANDATORY PROPERTY TESTS (updated):
- Same metadata + same bytecode → same digest
- Same metadata + DIFFERENT bytecode → DIFFERENT digest (F-059 critical test)
- Dictionary ordering differences do not alter the digest
- Digest is represented in a stable, auditable form

CRITICAL SECURITY RULE: spec_digest alone MUST NOT authorize an arbitrary caller-supplied object. A malicious tool reproducing public schema AND bytecode of an existing trusted tool must NOT become trusted. The registry MUST bind digest to a specific trusted executable instance captured at registration.

---

## PART 2 — SCHEMA v4.0 (Addressing F-057, F-058, F-060)

```json
{
  "schema_version": "EO-005-tasks-4.0",
  "phase": "EO-005",
  "execution_order": ["G4", "G6a", "G4b", "G5", "G6b", "G8", "G8b"],
  "path_policy": "allowed_paths is STRICT WHITELIST (default-deny). forbidden_paths is redundant defense-in-depth.",
  "tasks": [
    {
      "task_id": "G6a",
      "name": "Evidence Infrastructure Setup (Split from G6 per F-058)",
      "dependencies": ["G4"],
      "preconditions": ["G4 passes Gemini re-audit"],
      "allowed_paths": [".github/workflows/evidence-check.yml", "scripts/validate_evidence.py", ".evidence/.gitkeep"],
      "requirements": [
        "Create scripts/validate_evidence.py enforcing schema: base_sha, head_sha, test_result, lint_result, model_id, timestamp",
        "Create .github/workflows/evidence-check.yml (blocking CI)",
        "CI MUST reject PRs without valid .evidence/EO-*.json",
        "EXECUTOR MUST NOT BE GROK (I-026 compliance)",
        "Validator MUST verify Audit_Token signature against Gemini's GPG public key"
      ],
      "executor": "deepseek",
      "audit_token_required": true
    },
    {
      "task_id": "G4b",
      "name": "Close G4 with full adversarial proof (Updated per F-057)",
      "dependencies": ["G6a"],
      "preconditions": ["G6a merged into main", "G4 re-audit passed"],
      "allowed_paths": ["tests/test_tool_identity.py", ".evidence/EO-005-g4.json", "docs/EO-005.md"],
      "requirements": [
        "All 16 mandatory tests from Re-Audit Contract MUST be present and passing",
        "TEST-01 (forged ID), TEST-02 (TOCTOU), TEST-03 (Sandbox), TEST-04 (Memory Poisoning) explicitly required",
        "Update .evidence/EO-005-g4.json with TRUE test/lint results from CI",
        "AUDIT_TOKEN FIELD: Grok MUST leave audit_token field NULL",
        "audit_token will be injected out-of-band by CI step controlled by DeepSeek/Human Director using Gemini's signed token",
        "Grok is FORBIDDEN from writing, guessing, or copying any Audit_Token value",
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
        "   - Operational (ToolExecutionError, TimeoutError, IOError) → Result.err(), continue",
        "   - Security (SandboxViolation, SecurityDowngradeError, HashMismatchError, CapabilityViolationError) → bypass Result, HARD CRASH, halt loop, WAL CRITICAL entry",
        "   - Must use isinstance() checks, NOT broad except Exception",
        "Full 10-stage integration test",
        "Zero imports of legacy ToolRegistry"
      ],
      "executor": "grok",
      "audit_token_required": true
    },
    {
      "task_id": "G6b",
      "name": "Final Evidence Closure Validation (Split from G6 per F-058)",
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
      "name": "Council Roster Update (Separated per F-052)",
      "dependencies": ["G8"],
      "preconditions": ["G8 CLOSED"],
      "allowed_paths": ["docs/MOSAABAI_MASTER_v1.0.5_FULL.md"],
      "requirements": [
        "Update Council roster with Grok's formal membership (execution-only role)",
        "Explicitly document: Grok has NO executive, merge, or audit authority",
        "Add Human Director sign-off block"
      ],
      "executor": "deepseek",
      "audit_token_required": true
    }
  ]
}
