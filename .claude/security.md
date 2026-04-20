# Security

## 4-Gate Security Pipeline

| Gate | Tool | Where | Blocks merge? |
|------|------|--------|---------------|
| 1 | **Gitleaks** — secrets detection | CI (GitHub Actions) + pre-commit hook | Yes (CI) |
| 2 | **npm audit** — dependency scanning | CI `security` job | Yes (`--audit-level=moderate`) |
| 3 | **security-reviewer agent** — SAST | Run via `/security-reviewer` before PRs touching auth/API | Expected on all auth PRs |
| 4 | **OWASP DoD** — acceptance criteria | Definition of Done checklist in every PR | Manual check |

## OWASP Top 10 Mitigations

| # | Risk | Mitigation |
|---|------|------------|
| A01 | Broken Access Control | Clerk middleware on `/stats`, `/settings`; `auth()` check in API routes |
| A02 | Cryptographic Failures | No custom crypto; Clerk manages sessions; Neon enforces TLS |
| A03 | Injection | Prisma ORM — parameterized queries only; zero raw SQL |
| A04 | Insecure Design | Auth required for all prediction/player data (PII-adjacent) |
| A05 | Security Misconfiguration | `.env.local` git-ignored; all secrets in Vercel + GitHub Secrets |
| A06 | Vulnerable Components | `npm audit --audit-level=moderate` in CI blocks on HIGH |
| A07 | Authentication Failures | Clerk handles MFA, token rotation, session invalidation |
| A08 | Integrity Failures | Gitleaks in CI + pre-commit; no unsigned artifacts |
| A09 | Logging Failures | Vercel captures all API requests; no PII in logs |
| A10 | SSRF | No user-controlled URLs fetched server-side |

## Definition of Done — Security Acceptance Criteria

Every PR must satisfy before merge:

- [ ] No new HIGH/CRITICAL findings in `npm audit`
- [ ] Gitleaks CI gate passes (no secrets committed)
- [ ] PRs touching `/app/api/` or `middleware.ts` reviewed by `security-reviewer` agent
- [ ] All DB queries use Prisma (no template literals with user input)
- [ ] New environment variables added to `.env.example` (never `.env.local`)

## Secrets Management

- Never commit `.env.local` or `.env`
- Store production secrets in Vercel Environment Variables
- Store CI secrets in GitHub Actions Secrets
- Rotate keys immediately if accidentally committed (use `git filter-repo`)
