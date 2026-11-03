# OWASP Top 10:2025 mapping for MCP servers

Category-by-category mapping between the OWASP Top 10:2025 and this skill's six-stage guardrail pipeline (see SKILL.md). Use it during audits to show which controls cover which category, and to identify what remains the responsibility of the surrounding platform (host, gateway, IdP, CI/CD).

Load the sibling references for the categories the pipeline does not fully cover on its own:

- [supply-chain-and-integrity.md](supply-chain-and-integrity.md) — A03, A08
- [crypto-secrets-and-misconfiguration.md](crypto-secrets-and-misconfiguration.md) — A04, A02
- [injection-and-exceptional-conditions.md](injection-and-exceptional-conditions.md) — A05 (traditional), A10

## Mapping table

| OWASP 2025 category | MCP-specific threat | Where covered | Evidence to request |
|---|---|---|---|
| A01 Broken Access Control | Client/LLM supplies another user's ID (IDOR/BOLA); confused deputy via token passthrough | Stage 1 per-tool scopes; stage 3 token-derived identity, ownership checks, "not found" responses | Phase 1 and 3 tests; eval 1 |
| A02 Security Misconfiguration | Debug mode, wildcard CORS, permissive containers, open network rules, undocumented metadata exposure | Stage 1 metadata policy; crypto-secrets-and-misconfiguration.md | Deployment checklist; config review |
| A03 Software Supply Chain Failures | Vulnerable or malicious dependency in the JWT/DLP/schema stack; unreviewed transitive packages | supply-chain-and-integrity.md | SBOM, lockfile, CI scan gate |
| A04 Cryptographic Failures | Tokens/PII stored or transmitted unprotected; weak or confused JWT algorithms | Stage 1 algorithm allowlist and JWKS discipline; crypto-secrets-and-misconfiguration.md | TLS scan; key-management review |
| A05 Injection | Direct/indirect prompt injection; SQL, command, or template injection inside tool code | Stage 2 (LLM injection); injection-and-exceptional-conditions.md (traditional injection) | Phase 2 corpus tests; static scan |
| A06 Insecure Design | Generic pass-through tools; single-step payments; missing limits and idempotency | Tool surface design; stage 3 prepare/confirm and limits | Phase 0 and 3 tests; evals 7-8 |
| A07 Authentication Failures | `alg: none`, algorithm confusion, wrong `aud`/`iss`, stale MFA, token replay | Stage 1 | Phase 1 tests; eval 2 |
| A08 Software or Data Integrity Failures | Tool poisoning; tampered confirmation payloads; unsigned artifacts; spoofed webhooks | Stage 2 static descriptions; stage 3 payload binding; supply-chain-and-integrity.md | Phase 2/3 tests; pipeline review |
| A09 Security Logging and Alerting Failures | Attacks invisible because decisions are not logged, or successful-call anomalies are not alerted | Stage 5 audit and anomaly alerts | Phase 4-5 tests; SIEM rules |
| A10 Mishandling of Exceptional Conditions | Fail-open DLP; double charge after a crash; retry storms; partial state | Fail-closed rules in every stage; injection-and-exceptional-conditions.md | Failure-injection tests per phase |

## How to use in an audit

1. For each category, record one of: **covered by pipeline**, **covered by reference guidance**, **platform responsibility** (IdP, gateway, CI/CD), or **not applicable** — always with evidence.
2. A category counts as covered only when a test or configuration artifact proves it, not merely a design statement.
3. Report gaps with severity and the smallest control that closes each one.

## Out of scope (platform responsibilities)

- **Host/gateway**: final-response validation (stage 6), TLS termination policy, WAF rules.
- **IdP**: account lockout, credential-stuffing defenses, MFA enrollment flows.
- **CI/CD platform**: runner isolation, secret storage for the pipeline itself.

When the MCP server depends on any of these, document them as explicit requirements for the platform rather than assuming they exist.
