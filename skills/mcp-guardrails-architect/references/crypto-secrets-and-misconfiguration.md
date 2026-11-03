# Cryptography, secrets, and deployment configuration (OWASP A04, A02)

## Cryptographic failures (A04)

- **TLS 1.2+ on every hop**: client to server, server to provider, server to IdP (JWKS). Certificate and hostname validation MUST NOT be disabled — `verify=False`, `ssl._create_unverified_context`, and `CERT_NONE` are release blockers.
- **Encryption at rest** for stored tokens, PII, and payment data: envelope encryption with a KMS-managed key; never application-managed static keys in environment files.
- **Key management lifecycle**: generation inside the vault/KMS, a documented rotation schedule, a revocation procedure, and destruction. SKILL.md section 4.2 covers JWKS rotation; apply the same discipline to every key.
- **Secrets live in a vault** (Vault, Secret Manager, KMS); never in source control, container images, logs, or LLM context (SKILL.md stages 3-5). Rotate any secret that has ever appeared in a log or prompt.
- **Passwords/verifiers**, if any exist, use Argon2id or bcrypt with a per-user salt; never bare fast hashes (MD5, SHA-1, SHA-256).
- **Backups and replicas** are encrypted with the same rigor as primary storage; test restore procedures.
- **Token storage**: if provider or refresh tokens must be stored, store them encrypted, bound to `sub`, with expiry and revocation. Access tokens SHOULD NOT be persisted at all.

## Security misconfiguration (A02)

- **Secure defaults, deny by default**: every pipeline control fails closed (SKILL.md); configuration makes the safe path the default path.
- **Debug off in production**: framework debug mode, interactive consoles, and verbose error pages are release blockers; clients receive sanitized error codes (SKILL.md stage 3).
- **CORS**: explicit origin allowlist; MUST NOT combine `*` with credentials; prefer no CORS at all for server-to-server MCP traffic.
- **Security headers** where HTTP is exposed to browsers: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options`, and `Cache-Control: no-store` on sensitive responses.
- **Containers**: run as non-root, read-only root filesystem, drop all capabilities, minimal base image, no shell or package manager in the final image where feasible.
- **Cloud IAM**: least-privilege roles; no wildcard actions or resources; separate roles per environment; no long-lived static credentials.
- **Network**: the server is not publicly reachable unless required; egress is allowlisted (SKILL.md stage 3); security groups deny by default.
- **Startup config validation**: fail fast on missing or weak configuration (default secrets, wildcard hosts, disabled verification); never boot into a permissive fallback.
- **Discovery metadata**: the exposure decision for tool listings and metadata is explicit and documented (SKILL.md stage 1); public responses contain no sensitive information.
- **Default credentials**: none, anywhere; setup requires explicit secret provisioning.

## Checklist

- [ ] TLS enforced on every hop; verification never disabled; automated TLS scan in CI.
- [ ] PII/tokens encrypted at rest with KMS-managed keys; rotation and revocation documented.
- [ ] No secrets in repo, images, logs, or prompts (automated secret scan in CI).
- [ ] Debug mode off; sanitized error contract verified by tests.
- [ ] CORS allowlist explicit; security headers present; sensitive responses `no-store`.
- [ ] Container non-root, read-only filesystem, dropped capabilities; IAM roles least-privilege.
- [ ] Startup fails fast on missing or weak configuration.
