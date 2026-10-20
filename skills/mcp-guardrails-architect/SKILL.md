---
name: mcp-guardrails-architect
description: "Design, implement, review, or audit input and output guardrails for MCP servers (especially FastMCP Resource Servers) that expose tools handling sensitive data such as payments, card numbers, personal identifiers, or tokens. Use for MCP tools, OAuth/JWT/MFA validation, input schemas, output DTOs, DLP, masking, audit logging, prompt injection, confused deputy risks, or questions about preventing sensitive data leaks in MCP/LLM systems."
---

# MCP Guardrails Architect

Guidance for designing and auditing a six-stage guardrail pipeline for a **FastMCP Resource Server**: **before the tool** (stages 1–2), **tool execution** (stage 3), and **after the tool** (stages 4–6).

This skill provides requirements, patterns, pseudocode, and checklists; it does not provide a complete implementation. Produce architecture decisions and verifiable acceptance criteria, and leave implementation to the project team unless the user explicitly asks for code.

## 1. Skill definition

### 1.1 Purpose

Ensure every MCP tool call follows this sequence: authentication and scope authorization → input guard → execution using token-derived identity → output DTO and masking → output DLP and auditing → final response validation. Apply **Zero Trust**, **Deny by Default**, **Least Privilege**, **Defense in Depth**, and **Fail Closed**.

### 1.2 When to activate

- Creating or changing a tool, resource, or prompt on an MCP server.
- Configuring OAuth 2.1, OIDC, JWT, JWKS, or MFA on a Resource Server.
- Defining tool input schemas or output DTOs.
- Working with tools that access financial or personal data (card numbers, CPF/CNPJ, tokens, balances, or statements).
- Reviewing, threat-modeling, or auditing an MCP server.
- Asking about direct or indirect prompt injection, data leakage, confused deputy risks, or LLM-mediated exfiltration.

### 1.3 Mental model

| Principle | Architectural consequence |
|---|---|
| The **LLM is not a trust boundary** and can be manipulated by prompt injection. | The LLM does not enforce security controls. Identity, authorization, schema validation, and redaction are enforced by the server. A classifier may provide an additional risk signal, but it does not replace deterministic controls. |
| The **MCP client presents the token**. | The server never trusts `user_id`, `account_id`, or `cpf` supplied as tool arguments. |
| **Authentication is handled through an IdP** with OAuth and, where required, MFA. | Credentials must not enter the LLM context. |
| Sensitive data leaves only through an **allowlist**. | New provider fields do not leak by default. |
| Validation failures **block**. | An error, timeout, or uncertainty results in a safe generic response, never a passthrough. |

### 1.4 Pipeline

```text
MCP client + LLM --Bearer--> [1 Authn/Scope] -> [2 Input Guard] -> [3 Tool Execution] --> Provider
                                  BEFORE TOOL                    TOOL
[3] -> [4 DTO + Masking] -> [5 Output DLP + Audit] -> [6 Final Response Validation] -> User
                  AFTER TOOL
IdP (OAuth + MFA) --JWKS--> [1]
```

## 2. Implementation guidance

### Stage 1 — Authentication and scope (before the tool)

**Implement**

- Extract the Bearer access token from the `Authorization` header. Reject tokens in query strings or request bodies.
- Validate the signature using the IdP's public keys (JWKS), and validate the `iss`, `aud`, `exp`, `nbf`, `iat`, `sub`, and `scope` claims; validate `jti` if used.
- Authorize **per tool**: each tool declares its minimum required scope(s). Deny when required scopes are missing.
- Require **fresh MFA** for sensitive tools (payments, full personal-data access, or profile changes).

**Security requirements**

- **Algorithms**: explicitly allowlist asymmetric algorithms (`RS256`, `ES256`, or `EdDSA`). Reject `none` and symmetric algorithms (`HS*`) when using a public key, preventing algorithm confusion. The algorithm comes from server configuration, never from the token header.
- **`aud` (audience)**: require a token issued for **this** Resource Server (use resource indicators, RFC 8707). Reject tokens issued for another service. **Never pass the received token through to downstream APIs**; use token exchange (RFC 8693) or a per-user credential.
- **`iss`**: compare against a fixed configured value, never a value derived from the token.
- **Fresh MFA**: validate `acr`/`amr` according to the IdP's documented claim semantics **and** require `auth_time` to be within a short window (for example, 5–10 minutes for payments; define it per tool). Do not assume that a literal `"mfa"` value is standardized across IdPs. If MFA is stale, return the protocol-appropriate authorization error and, where supported, a *step-up* challenge (RFC 9470, `insufficient_user_authentication`) so the client can reauthenticate **outside the chat**.
- **Short lifetime**: access tokens should last 5–15 minutes; refresh tokens must never reach the MCP server.
- Allow clock skew of no more than 60 seconds.
- **Opaque errors**: 401/403 responses must not reveal which claim failed; detailed reasons belong only in the audit log.
- Rate-limit by `sub` and IP before expensive processing.
- Optional for high-risk deployments: use sender-constrained tokens (DPoP, RFC 9449, or mTLS) to prevent replay of stolen tokens.

**Technologies and approaches**

- Use a mature JWT library with a fixed-algorithm verification configuration and a dedicated JWKS client/cache.
- Apply authentication and authorization consistently to every protected operation using the framework's supported middleware/provider. Decide explicitly, based on deployment exposure and client requirements, whether discovery metadata or tool listings are public; if exposed, keep them free of sensitive information. Never let a public listing imply that tool invocation is authorized.
- Publish Resource Server metadata (RFC 9728, `/.well-known/oauth-protected-resource`) so clients can discover the correct IdP.

**Pseudocode**

```text
function authorize(request, tool):
    token = bearer(request) or deny(401)
    claims = verify_signature(token, jwks, alg_allowlist)   # failure -> deny
    require claims.iss == CONFIG.issuer
    require CONFIG.resource_id in claims.aud
    require claims.sub is non-empty
    require claims.iat <= now + skew
    require claims.exp > now - skew
    if claims.nbf exists:
        require claims.nbf <= now + skew
    require tool.required_scopes ⊆ claims.scope
    if tool.sensitivity >= HIGH:
        require mfa_satisfied(claims.acr, claims.amr, CONFIG.idp_mfa_policy)
        require now - claims.auth_time <= tool.max_mfa_age   # otherwise step-up
    return Identity(sub=claims.sub, scopes=claims.scope)     # immutable from here on
```

Validate required claims and their types before using them. Treat token timestamps, scope representation, and MFA claim semantics according to the token profile and IdP configuration; malformed or missing required claims are rejected.

### Stage 2 — Input guard (before the tool)

**Implement**

- A **strict schema** for each tool's arguments.
- An **anti-injection layer** for every free-text field.
- Normalization and limits before validation.

**Security requirements**

- **Strict schema** means exact types (no implicit coercion), `additionalProperties: false` (reject unknown fields), enums for finite values, anchored format patterns, maximum string/array lengths, numeric ranges, and monetary values as integer minor units (cents) or fixed-scale decimals, never floats.
- **Identity is never an argument.** A tool must not accept `user_id`, `cpf`, `account_owner`, etc. when these can be derived from the token. Resource IDs (for example, `payment_id`) require an ownership check in stage 3 to prevent IDOR/BOLA.
- **Normalize before checking**: Unicode NFKC, removal of control and zero-width characters, trimming, and size limits. This helps prevent regex bypasses using homoglyphs or invisible characters.
- **Layer defenses against injection**; no single layer is sufficient:
  1. Deterministic heuristics (patterns such as “ignore previous instructions,” “system prompt,” role-play attempts, fake delimiters, or URLs/Markdown intended for exfiltration).
  2. Optionally, a dedicated prompt-injection classifier as an additional risk signal for free-text fields. It must not replace authorization, schema validation, output controls, or other deterministic checks.
  3. Minimize the attack surface: use as few free-text fields as possible; prefer enums and IDs.
- **Indirect injection**: third-party data (transaction descriptions, beneficiary names, provider text) is **untrusted data**, never instructions. This also applies to tool output (see stage 4).
- Define an explicit classifier policy per tool/field sensitivity. If the classifier is designated a mandatory control for an operation, its failure or timeout must reject that operation (fail closed). If it is an optional signal, continue applying deterministic controls, record the classifier failure, and alert as appropriate. Never treat classifier output as proof that input is safe.
- Measure false positives and false negatives on representative, privacy-safe data before using classifier scores to block requests; document thresholds, exception handling, and user-visible recovery.
- **Idempotency**: write tools require an `idempotency_key` to prevent duplicate operations during LLM retries.
- Tool descriptions are static and versioned; never build descriptions dynamically from external data (prevents *tool poisoning*).

**Technologies and approaches**

- Python: Pydantic v2 in strict mode with `extra="forbid"`. TypeScript: Zod `.strict()`. Alternatively, validate JSON Schema with `additionalProperties: false`.
- Use anchored regexes without catastrophic backtracking (ReDoS); prefer named validators over ad hoc regexes.
- If used, run the injection classifier as an internal service with a latency SLO, explicit timeout policy, documented failure mode, and measured error rates.

**Pseudocode**

```text
function guard_input(raw_args, tool):
    args = normalize(raw_args)                       # NFKC, strip controls/zero-width chars
    args = schema(tool).validate_strict(args)        # types, limits, extra=forbid; failure -> deny
    for field in tool.free_text_fields(args):
        if deterministic_rules.block(field):
            audit.log("input_blocked", reason="injection"); deny
        if tool.classifier_policy(field) == REQUIRED:
            score = injection_classifier.score(field)  # error/timeout -> deny
            if score >= tool.classifier_threshold(field):
                audit.log("input_blocked", reason="classifier"); deny
        else:
            # Optional classifier failure is recorded; deterministic controls still apply.
            classifier.observe_if_available(field)
    return args
```

### Stage 3 — Tool execution

**Implement**

- The tool receives `Identity` (from the token) and validated `args`, then calls the payment provider.
- Perform object-level authorization before acting.

**Security requirements**

- **Identity comes from the token**: `sub` (mapped internally to a customer/account) is the only source of the user's identity. Arguments must never override it.
- **Ownership check**: every resource accessed or changed must belong to `sub`; otherwise respond “not found” without confirming that the resource exists.
- **Least privilege downstream**: use provider credentials with minimum scope; prefer token exchange or per-user credentials over a shared “master” key. Store secrets in a vault (Vault/Secret Manager), never in LLM context or logs.
- **Write operations (payments)**: apply per-user and per-tool amount limits, require explicit confirmation outside the chat (step-up/fresh MFA, already required in stage 1), and enforce idempotency.
- **Controlled egress**: allowlist outbound hosts; do not accept arbitrary URLs in arguments (prevents SSRF).
- **Resilience**: use short timeouts, a circuit breaker, and retries only for idempotent operations.
- **Sanitized errors**: convert provider exceptions to application-defined error codes. Never return stack traces, SQL, internal URLs, or raw payloads to the LLM.

**Pseudocode**

```text
function run_tool(identity, args, tool):
    resource = repo.find(args.resource_id)
    require resource and resource.owner == identity.sub    # otherwise "not found"
    require tool.within_limits(identity, args)
    result = provider.call(creds_for(identity), args, timeout=T, idempotency=args.key)
    return result                                          # still RAW: do not expose it yet
```

### Stage 4 — DTO and masking (after the tool)

**Implement**

- Convert the provider's raw result into a **per-tool output DTO** containing only fields on an **allowlist**.
- Mask each field according to its data classification.

**Security requirements**

- **Allowlist, not blocklist**: discard fields not declared in the DTO. New provider fields must not appear without an explicit decision.
- **Never serialize** the provider object or domain entity directly.
- **Mask by data type** (document the policy and align it with PCI DSS and applicable privacy law):
  - **PAN**: never expose the full value; at most expose the first 6 (BIN) and last 4 digits, or only the last 4. CVV, track data, and PIN must never appear in output.
  - **CPF/CNPJ**: partially mask (for example, expose middle digits only when justified); expose the full value only when necessary and under a specific scope.
  - **Tokens/secrets/keys**: never expose them; the provider must not return credentials to the LLM.
  - **Contact data, addresses, names**: minimize according to purpose.
- Treat provider **free text** (descriptions, memos) as **untrusted**: truncate, sanitize, and mark as data rather than instructions to mitigate indirect injection.
- Limit response volume with pagination and a maximum number of items/fields per response.

**Technologies and approaches**

- Use typed response models (Pydantic/Zod) with an `ignore` policy for extra fields and centralized, tested masking functions (one module; no duplicated per-tool masking logic).
- Maintain data classification (public, internal, PII, financial-sensitive) in a versioned catalog referenced by DTOs.

**Pseudocode**

```text
function to_dto(raw, tool):
    dto = {}
    for field in tool.output_allowlist:                  # declared fields only
        dto[field] = mask(raw[field], policy[field])     # mask_pan / mask_cpf / drop
    dto.free_text = sanitize_untrusted(truncate(raw.text))
    return dto
```

### Stage 5 — Output DLP and auditing (after the tool)

**Implement**

- Run DLP over the **serialized** DTO (the last deterministic server-side barrier).
- Record an audit entry for the decision.

**Security requirements**

- **Use validated detectors, not regex alone**:
  - **PAN**: 13–19 digit sequences (allowing spaces/hyphens) **and** Luhn validation.
  - **CPF/CNPJ**: formatted or unformatted values **and** check-digit validation.
  - **Tokens/secrets**: JWT pattern (`xxx.yyy.zzz` base64url), `Bearer` prefix, known API key patterns, and entropy detection for long random strings.
  - Other types: email, phone, PIX keys, IBAN, as appropriate for the domain.
- **Normalize before detection** (remove separators, apply Unicode NFKC) to resist formatting-based evasion.
- **Action by severity**: *redact* (replace with a marker such as `[REDACTED:CPF]`) for partial PII; *block* (reject the entire response) for secrets, full PANs, and tokens.
- **Auditing**: write a structured per-call log with `correlation_id`, `sub` (or a hash), tool, scopes, each stage's decision (allow/deny/redact/block), count and **type** of redacted items, and latency. **Never log sensitive values** or cleartext arguments; log an argument hash only when traceability is needed.
- Use immutable (append-only) logs, defined retention (LGPD), restricted access, and alerts for spikes in blocks/redactions (possible attack or bug).
- **Fail closed**: a DLP error blocks the response; never pass it through.

**Technologies and approaches**

- Use a PII detection library (for example, Presidio or equivalent) with custom recognizers for CPF/CNPJ/PIX, plus regex and checksum validators.
- Send structured JSON logs to a SIEM and track redaction metrics by type.

**Pseudocode**

```text
function dlp_and_audit(dto, ctx):
    text = normalize(serialize(dto))
    findings = detectors.scan(text)                      # regex + Luhn + mod-11 + entropy
    if any(f.severity == BLOCK for f in findings):
        audit.log(ctx, decision="block", types=types(findings)); deny
    dto = redact(dto, findings)
    audit.log(ctx, decision="allow", redacted=count_by_type(findings))
    return dto                                           # internal error -> deny
```

### Stage 6 — Final response validation (outside FastMCP)

> This stage runs **after** the LLM composes its response to the user, so it belongs in the orchestrator/gateway/host, not in the Resource Server (the MCP server cannot see the final text). If you do not control the host, implement it in a gateway between the LLM and user, or document it as a client requirement.

**Implement**

- Run DLP again on the **final text** (the LLM may reconstruct, concatenate, or reformat sensitive data).
- **Grounding**: transaction-specific or other security-sensitive claims (for example, payment status, amount, date, account/resource identifiers, and ownership) must be traceable to authorized tool output from this conversation. General explanations that do not assert facts about the user's transaction may rely on clearly identified trusted documentation or be framed as general guidance.
- Apply a **fail-closed** delivery policy.

**Security requirements**

- **Final DLP**: apply the stage 5 detectors to the composed text, including patterns that arise only through concatenation.
- **Grounding**: extract high-impact entities and claims from the response (for example, payment status, amount, date, and transaction/account identifiers) and verify them against the relevant authorized tool result using normalized comparisons. Block or regenerate unsupported or conflicting transaction claims. Keep general explanatory statements distinct from transaction-specific facts; if they need external support, use a trusted source appropriate to the deployment rather than treating MCP tool output as the only possible source. Never confirm a payment without evidence in tool output.
- **Rendering-based exfiltration**: block links, images, and Markdown with dynamic URLs containing data; allow only approved domains.
- **Fail closed**: if any validator fails, times out, or finds a mismatch, show the user a safe generic message (for example, “I couldn’t complete this safely”) with a `correlation_id` for support. Never deliver the original LLM text “just in case.”

**Pseudocode**

```text
function validate_final(answer, tool_outputs, ctx):
    if dlp.scan(answer).has_block_or_unredacted: deny
    for claim in extract_high_impact_claims(answer):     # payment facts, amounts, dates, IDs
        require grounded_in_authorized_output(claim, tool_outputs)
    require general_factual_claims_are_clearly_scoped_or_sourced(answer)
    require links_in_allowlist(answer)
    return answer
on any error/timeout: return SAFE_FALLBACK_MESSAGE      # fail closed
```

## 3. Acceptance criteria and tests

Mark an item as passed only when supported by evidence (logs, automated tests, or captures). Run all security tests in CI and whenever schemas, DLP rules, or security dependencies change.

### Phase 1 — Authentication, scope, and MFA

- [ ] Request without a token → 401, with no informative response body.
- [ ] Token with an invalid or altered signature → 401.
- [ ] Token with `alg: none` → 401.
- [ ] Token signed with HS256 using the public key as the secret (algorithm confusion) → 401.
- [ ] `iss` differs from the configured issuer → 401.
- [ ] `aud` identifies another Resource Server → 401 (and no downstream token passthrough occurs).
- [ ] Missing/empty `sub`, missing required claims, malformed claim types, or a future `iat` beyond allowed clock skew → 401.
- [ ] Expired token (`exp`) or token with a future `nbf` → 401.
- [ ] Unknown `kid` triggers a rate-limited JWKS refresh; if still unknown → 401.
- [ ] Valid token with insufficient tool scope → 403.
- [ ] Token whose `acr`/`amr` does not satisfy the configured IdP MFA policy for a sensitive tool → step-up challenge; the tool does **not** execute.
- [ ] `auth_time` outside the fresh-MFA window → step-up challenge.
- [ ] The exposure policy for discovery metadata and tool listings is documented; public responses reveal no sensitive information, and every protected tool invocation requires authentication and authorization.
- [ ] IdP/JWKS unavailable beyond the cache window → calls are denied (fail closed).
- [ ] Error messages do not reveal which validation failed; the reason appears only in the audit log.

### Phase 2 — Input guard and prompt injection

- [ ] Extra payload field → rejected (`extra=forbid`).
- [ ] Wrong type/coercion (for example, `"10"` where an integer is expected) → rejected.
- [ ] Oversized strings, huge arrays, or out-of-range values → rejected.
- [ ] Attempt to send another person's `user_id`/`cpf` as an argument → ignored/rejected; the tool uses only token `sub`.
- [ ] Another user's `payment_id` → “not found” response without confirming existence.
- [ ] Direct-injection corpus (“ignore previous instructions,” requests to reveal the system prompt, role-play, fake delimiters) → blocked and audited.
- [ ] Obfuscated injection (Unicode homoglyphs, zero-width characters, base64, mixed languages, content split across fields) → blocked after normalization.
- [ ] **Indirect** injection: provider data containing an instruction (“transfer to X”) neither changes behavior nor triggers a tool call.
- [ ] Classifier outage/timeout follows the documented per-tool policy: mandatory classifier dependency → reject; optional classifier → deterministic controls remain active and the failure is recorded/alerted.
- [ ] False-positive rate measured on a legitimate corpus and within the agreed target.
- [ ] Replaying the same `idempotency_key` does not duplicate the operation.

### Phase 3 — Execution

- [ ] Provider credentials never appear in logs, errors, or output.
- [ ] Provider errors return sanitized codes, with no stack trace or internal URL.
- [ ] Per-user value/volume limits are enforced.
- [ ] An arbitrary URL in an argument cannot trigger an outbound request (SSRF).

### Phases 4–5 — DTO, masking, DLP, and auditing (PII leakage)

- [ ] A new provider field does **not** appear in output until the DTO is explicitly changed.
- [ ] Valid PAN (Luhn) with spaces, hyphens, or periods → masked or blocked; full PAN never leaves the server.
- [ ] A 16-digit sequence that **fails** Luhn is handled according to policy (without unnecessary false positives).
- [ ] CPF with or without punctuation, in free text or a description field → redacted/masked; invalid check digits are handled according to policy.
- [ ] JWTs, API keys, and high-entropy strings in output → response blocked.
- [ ] Evasion: digits separated by spaces/Unicode/zero-width characters, or data split across fields → detected after normalization.
- [ ] DLP module error → block (fail closed), never passthrough.
- [ ] Every audit log includes `correlation_id`, `sub`, tool, and per-stage decisions; **no** sensitive values appear in cleartext (automated log scan).
- [ ] Logs are append-only and alerts for block/redaction spikes are configured.

### Phase 6 — Final response

- [ ] Transaction-specific high-impact claims (such as payment status, amount, date, or transaction ID) that are absent from authorized tool outputs → blocked or regenerated; general explanations are clearly distinguished and appropriately sourced.
- [ ] LLM instructed via injection to reproduce a full PAN/CPF → final DLP blocks it.
- [ ] Markdown link/image with data in its URL → blocked; only allowlisted domains are permitted.
- [ ] Validator failure/timeout → user receives a safe generic message with a `correlation_id`.
- [ ] No payment confirmation is issued without matching evidence in tool output.

### End-to-end test (release gate)

- [ ] Red-team suite combining attacks (stolen token + injection + exfiltration) runs with no data leakage.
- [ ] Threat model (STRIDE and OWASP Top 10 for LLMs) is reviewed and updated for the change.
- [ ] Load test confirms guardrail overhead meets the SLO and behavior remains fail-closed under load.

## 4. Maintenance and evolution

### 4.1 Schema evolution without breaking clients

- **Version**: breaking changes create a new tool version (for example, `pay_v2`) rather than modifying the existing one; keep the old version for an announced deprecation window.
- **Compatible changes**: add an **optional** field with a default; expand an enum carefully (older clients may not recognize a new output value).
- **Breaking changes**: remove/rename a field, make an optional field required, or narrow a type/range. These require a new version.
- **Strict input, tolerant output**: the server rejects extra input fields; clients should ignore unknown output fields. Document this in the contract.
- **Contract tests**: maintain consumer-driven contract tests in CI; schema changes pass only if valid contracts remain accepted.
- Change the output allowlist only after an explicit security review (a new field requires a conscious classification and masking decision).
- Update the schema, DTO, masking policy, tests, and tool documentation together. Version and review tool descriptions (to mitigate tool poisoning).

### 4.2 JWKS key management and rotation

- **Trusted source**: configure a fixed JWKS URL accessed over TLS; never derive it from a token claim.
- **TTL cache**: use a cache (for example, minutes to a few hours) and respect cache headers. Refresh **immediately and with rate limits** when an unknown `kid` appears (to avoid DoS and rotation delays).
- **Overlapping rotation**: the IdP publishes the new key **before** signing with it and keeps the old key until all tokens signed with it have expired. The server accepts multiple `kid` values simultaneously.
- **Bounded stale window**: if JWKS is unavailable, use the cache only up to a defined maximum; after that, **deny** (fail closed).
- **Emergency revocation**: document how to remove a compromised `kid` from JWKS and invalidate the cache across all instances; consider introspection/revocation lists for high-risk tokens.
- **Monitor**: alert on increases in signature failures, unknown `kid` values, and JWKS fetch errors. Periodically rehearse both normal and emergency rotation.
- Review the algorithm allowlist when the IdP changes algorithms.

### 4.3 DLP rule maintenance

- **Version rules as data** (detectors, patterns, thresholds, and per-type policies), with peer review and automated tests. Rule changes go through the same CI pipeline as code.
- **Living test corpus**: include positive cases (synthetic valid PAN, CPF, and tokens), negative cases (similar but non-sensitive numbers), and evasion cases. Add every incident or false negative as a permanent case. Use synthetic data only, never real data.
- **Metrics**: track redaction/block rates by type, reported false positives, and false negatives found in audits. Review periodically (for example, monthly) and after any incident.
- **New data types** (new tool, provider, or regulation): add a detector and classification **before** releasing the tool.
- **Shadow mode**: when hardening a rule, first run it in “log only” mode to measure impact, then enable blocking.
- **Compliance**: review policies against PCI DSS (PAN) and LGPD (CPF/PII, retention, minimization) when regulations change; retain audit evidence.
- **Injection classifier**: periodically reevaluate against an updated attack corpus; version the model and monitor degradation.

### 4.4 Continuous operations

- Review access and scopes (least privilege) quarterly.
- Review the threat model for every new tool or integration.
- Update security dependencies (JWT, DLP, schema) and scan for vulnerabilities in CI.
- Exercise incident response (PII leak, compromised key) using tested runbooks.

## 5. How to use this skill

1. Identify which stage (1–6) the request concerns and the tool's sensitivity.
2. Apply the relevant stage guidance. If the request spans multiple stages, review the pipeline in order.
3. For a review or audit, report:
   - **Summary**: compliant, partially compliant, or non-compliant.
   - **Findings by stage**, each with severity (critical, high, medium, low), evidence, and a recommendation.
   - **Uncovered checklist items** from section 3.
4. Immediately flag critical deviations: identity taken from arguments, token passthrough, unfixed JWT algorithms, direct serialization of provider objects, fail-open DLP, or a missing stage 6 control.
5. Do not write complete code by default. Provide pseudocode, expected behavior, and test guidance; implement code only when the user explicitly requests it.
