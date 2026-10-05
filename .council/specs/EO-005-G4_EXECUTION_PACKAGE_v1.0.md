# EO-005-G4 EXECUTION PACKAGE v1.0
AUTHOR: Auditor General (Gemini)
AUTHORITY: Human Director (Sole Merge Authority)
DATE: 2026-10-05
STATUS: BINDING

## SECTION 1: ARCHITECTURAL SECURITY MANDATES

CRIT-01: Legacy Purge - spawn_child() requires tool_id: str. No name fallback.
CRIT-02: Cryptographic Identity - spec_digest from metadata + bytecode + AST.
         co_freevars == () AND co_cellvars == () enforced at registration.
CRIT-03: AST Whitelist - allow only pure builtins. Ban Attribute, Import, Lambda, eval, exec, getattr, etc.
CRIT-04: Runtime Builtin Isolation - __globals__ with MappingProxyType-frozen builtins.
         The sandbox globals MUST be the ACTUAL execution namespace (not a computed unused variable).
CRIT-05: Read-Only Registry - MappingProxyType internally. No re-registration.
CRIT-06: Evidence - audit_token: null in Grok's artifacts. CI injects the token out-of-band.

## SECTION 2: TASK ORDER
G6a -> G4 -> G4b -> G5 -> G6b -> G8
G8b reserved for DeepSeek/Human Director only.

## SECTION 3: EVIDENCE SCHEMA
See .evidence/schemas/evidence_schema_v1.json

## SECTION 4: ACCEPTANCE CRITERIA (16 MANDATORY TESTS)
1. test_legacy_tool_registry_removed_or_unreachable
2. test_no_name_only_tool_authorization
3. test_spec_digest_is_deterministic
4. test_spec_digest_changes_when_code_changes
5. test_same_name_different_bytecode_rejected
6. test_freevars_and_cellvars_rejected_at_registration
7. test_registry_is_immutable_after_creation
8. test_registry_rejects_redefinition
9. test_registered_tool_mutation_cannot_change_trust
10. test_spawn_child_delegates_trusted_identity_not_name
11. test_spawn_child_rejects_missing_tool_id
12. test_ast_whitelist_blocks_attribute_access
13. test_ast_whitelist_blocks_aliased_eval_call
14. test_builtins_mutation_raises_type_error
15. test_unknown_digest_fails_closed
16. test_child_tool_set_remains_monotonic_by_identity
