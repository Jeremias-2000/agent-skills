# Traditional injection and exceptional conditions (OWASP A05, A10)

Prompt injection is covered by SKILL.md stage 2. This reference covers classical injection inside tool implementations, and the failure-handling discipline of A10.

## Traditional injection (A05)

- **SQL/NoSQL**: parameterized queries or the ORM's query builder only. MUST NOT build queries with f-strings, `%` formatting, `.format()`, or concatenation — even for "internal" tools. Input validation (SKILL.md stage 2) is defense in depth, never a substitute for parameterization. Use a least-privilege database user per service (no DDL, no cross-schema access).
- **OS commands**: avoid the shell; if a subprocess is unavoidable, use argument arrays (`shell=False`) with an allowlisted binary and validated arguments.
- **Templates and expressions**: never render user- or provider-supplied text through template engines, `eval`/`exec`, or expression languages. LLM-bound text is data, not code.
- **LDAP/GraphQL/others**: use the library's escaping or parameterization; disable GraphQL introspection and deep nesting in production where exposed.
- **Stored (second-order) injection**: data written by an earlier call and later read into LLM context is still untrusted — apply stage 4 sanitization on the way out, not only stage 2 on the way in.
- **Error leakage**: database or interpreter errors never reach the LLM (SKILL.md stage 3 sanitized errors); they reveal schema internals that aid injection.

## Exceptional conditions (A10)

- **Exception boundary**: catch at the adapter/entrypoint boundary and map to sanitized application error codes; uncaught exceptions MUST NOT propagate to the client.
- **Atomicity and compensation**: multi-step writes are atomic (single transaction) or compensated (saga with explicit rollback steps). A payment flow that crashes between "charge" and "record" MUST reconcile on recovery — query the provider by `idempotency_key` before any retry.
- **Partial failure policy**: define per tool what happens when the provider succeeds but post-processing (DTO, DLP, audit) fails. The safe default is deny/rollback, never silent passthrough.
- **Races and TOCTOU**: the ownership check and the action it guards are atomic (same transaction or a conditional update); enforce uniqueness with database constraints, not application checks alone. Idempotency keys are unique constraints, not best-effort flags.
- **Bounded retries**: retries only for idempotent operations, capped (for example 3), with exponential backoff and jitter; never retry on 4xx or on validation failure.
- **Resource exhaustion**: timeouts on every outbound call (SKILL.md stage 3), payload size caps (stage 2), response caps (stage 4), and concurrency limits per `sub` to survive retry storms from misbehaving clients or looping LLM agents.
- **Fail closed on uncertainty**: any ambiguous state — unknown charge status, DLP outage, mandatory-classifier timeout — resolves to deny plus a safe message with a `correlation_id` (SKILL.md stages 5-6).

## Checklist

- [ ] No string-built SQL anywhere (static scan in CI); least-privilege database user.
- [ ] No `shell=True`, `eval`/`exec`, or template rendering of untrusted text.
- [ ] Data read back from storage is sanitized before entering LLM context.
- [ ] Crash-between-steps scenario tested for every write tool (reconcile by idempotency key).
- [ ] Ownership check and mutation are atomic; idempotency enforced by a unique constraint.
- [ ] Retries bounded, idempotent-only, with backoff; timeouts and concurrency caps on all outbound calls.
- [ ] Uncaught-exception handler returns sanitized codes; covered by tests.
