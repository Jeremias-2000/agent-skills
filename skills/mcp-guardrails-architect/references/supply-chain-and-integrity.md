# Supply chain and integrity (OWASP A03, A08)

Controls for dependency, build, and data integrity. The guardrail pipeline is only as trustworthy as the code and data it runs.

## Dependency integrity (A03)

- **Pin everything.** Every direct dependency is pinned (`==` or an equivalent locked hash). MUST NOT deploy from unpinned requirements.
- **Commit a lockfile** (`uv.lock`, `poetry.lock`, `Pipfile.lock`, `pdm.lock`) and install from it in CI and production (`--locked` or `--require-hashes` where supported).
- **Generate an SBOM** (CycloneDX or SPDX) on every release and archive it as a build artifact.
- **Scan in CI** with a vulnerability scanner (`pip-audit`, `osv-scanner`, or equivalent) and fail the build on exploitable severities; track exceptions with expiry dates.
- **Review new dependencies like new code**: maintainer reputation, release cadence, transitive footprint. JWT, DLP, and schema libraries are part of the security boundary — treat their compromise as a security incident.
- **Verify provenance** where available (Sigstore signatures, SLSA provenance); prefer packages with published attestations for security-critical libraries.

## Build and deployment integrity (A08)

- **Sign build artifacts** (containers, wheels) and verify signatures before deploy; deploy only artifacts built by CI from a reviewed commit.
- **Protect the pipeline**: CI credentials are short-lived and least-privilege; build definitions are code-reviewed; third-party CI actions are pinned by commit SHA.
- **No runtime self-update**: the server never pulls code, models, or tool descriptions from external sources at runtime.

## Data and integration integrity (A08)

- **Webhook and callback authenticity**: verify HMAC signatures or mTLS on inbound provider callbacks; include a timestamp and nonce to reject replays; reject events older than a short window.
- **Tool description integrity**: tool names and descriptions are static, versioned, and reviewed (SKILL.md stage 2); never assemble them from external data at runtime.
- **Confirmation payload binding**: prepare/confirm tokens bind the exact payload hash (SKILL.md stage 3); any mutation invalidates the token.
- **Tamper-evident audit logs**: append-only storage with restricted write access (SKILL.md stage 5); alert on gaps or sequence breaks.
- **Deserialization**: never unpickle or otherwise deserialize untrusted data with native object deserializers; use strict JSON schemas (SKILL.md stage 2).

## Checklist

- [ ] Requirements fully pinned and lockfile committed; CI installs with `--locked`/`--require-hashes`.
- [ ] SBOM generated per release and archived.
- [ ] Vulnerability scan gate in CI; exceptions documented with expiry dates.
- [ ] Artifacts signed and verified before deploy; deploys only from CI-built commits.
- [ ] Inbound webhooks/callbacks signature-verified with replay protection.
- [ ] No runtime fetching of code, models, or tool descriptions from external sources.
