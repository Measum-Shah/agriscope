# AgriScope Security Architecture

This document specifies the security controls, authentication mechanisms, token lifecycles, and defense-in-depth measures implemented across the AgriScope platform.

---

## 1. Authentication & Token Lifecycle

- **JWT Access Token**:
  - **Lifetime**: 15 minutes.
  - **Payload**: User UUID (`sub`), role, plan, and a unique cryptographic `jti` nonce.
  - **Signature**: HMAC-SHA256 with rotation via `SECRET_KEY`.

- **Refresh Token & Family Rotation**:
  - **Transport**: Stored exclusively in an `httpOnly`, `Secure`, `SameSite=Lax` cookie mounted strictly on `/api/v1/auth`.
  - **Lifetime**: 7 days.
  - **Storage**: Raw refresh tokens are never persisted in plaintext; only the SHA-256 hash (`hashed_token`) is stored in the database.
  - **Rotation**: Every `/auth/refresh` request revokes the presented refresh token and issues a new one within the same `token_family`.
  - **Reuse Detection**: If an already revoked refresh token is presented (indicating theft or token replay), AgriScope instantly invalidates all sessions in that `token_family` (`revoked=true`, `reuse_detected=true`) and records a high-severity security audit event (`auth.token_reuse_detected`).

---

## 2. Password Policies & Account Lockout

- **Complexity Rules**:
  - Minimum 8 characters.
  - At least 1 uppercase letter.
  - At least 1 numeric digit.
  - Rejection of common/compromised passwords (e.g. `password123`, `agriscope123`).
- **Hashing**:
  - Passwords hashed using bcrypt with 12 salt rounds (`settings.BCRYPT_ROUNDS`).
- **Enumeration Resistance**:
  - Non-existent user login requests execute constant-time dummy bcrypt hashing to prevent timing-based user enumeration.
  - Generic message `"Invalid email or password."` returned on authentication failures.
- **Account Lockout & Auto-Unlock**:
  - 5 consecutive failed login attempts trigger a 15-minute lockout (`locked_until = now + 15 min`).
  - The lockout automatically expires after 15 minutes without requiring administrative manual intervention.
  - Consecutive failures reset to 0 upon successful authentication.

---

## 3. Email Verification & Password Recovery

- **Email Verification**:
  - Single-purpose signed action token (`type: "verify_email"`) with 24-hour expiration.
  - Dispatched via Celery worker with SMTP (Mailpit in development) or fallback direct mock provider.
- **Password Reset**:
  - Single-use signed action token (`type: "reset_password"`) with 1-hour expiration.
  - Tied to the user's current password hash signature (`pwd_ver`), guaranteeing immediate token invalidation once used.
  - Executing a password reset instantly revokes all active refresh token families and sessions across all devices (`logout-all`).

---

## 4. Rate Limiting & Audit Logging

- **Sliding-Window Rate Limiting**:
  - Backed by Redis sorted sets (`ZREMRANGEBYSCORE`, `ZADD`, `ZCARD`) with seamless in-memory fallback.
  - Enforced per endpoint: 20 req/min on general auth (`register`, `login`, `refresh`), 5 req/min on sensitive recovery routes (`forgot-password`, `resend-verification`, `reset-password`).
- **Audit Trails**:
  - Every authentication lifecycle event is written to `audit_logs` (`actor`, `action`, `target`, `metadata_json`, `ip_address`, `user_agent`, `timestamp`).
  - Indexed via composite index `(actor, timestamp)` for rapid security forensics.

---

## Threat Model Summary (OWASP ASVS Mapping)

### Architecture Boundaries
- **Public internet** → Nginx reverse proxy (TLS termination in prod)
- **Nginx** → FastAPI backend, Vite/React frontend, ML microservice
- **Backend** → PostgreSQL (least-privilege app user), Redis (in-memory secrets isolation), MinIO (presigned URLs)
- **Celery workers** → No direct internet access; queue via Redis

### OWASP ASVS Coverage

| ASVS Area | Control | Implementation |
|-----------|---------|----------------|
| V1 Architecture | Separation of ML service | Dedicated FastAPI ML microservice, separate network |
| V2 Authentication | Secure session management | httpOnly rotating refresh tokens, 30-day sliding window, reuse detection |
| V2 Authentication | MFA | TOTP RFC 6238, 8 hashed recovery codes |
| V2 Authentication | Brute-force protection | 5 failed attempts → 15-min auto-lockout; Redis rate limiter |
| V3 Session | Token revocation | Session table with force-logout; refresh family invalidation |
| V4 Access Control | RBAC | `require_role` dependency enforced on every admin route |
| V4 Access Control | Plan gating | `require_plan_feature` quota checks before Pro features |
| V5 Validation | Input validation | Pydantic v2 models on all request bodies; Zod on frontend |
| V5 Validation | Upload safety | File size limit (50 MB), CSV-only MIME validation, content scan |
| V5 Validation | CSV injection | CWE-1236 formula prefix sanitization in export service |
| V6 Cryptography | Password hashing | bcrypt (cost 12) via passlib |
| V6 Cryptography | API key storage | SHA-256 hash at rest, plaintext shown once |
| V7 Error Handling | Uniform error format | `{detail, code, request_id}` on all errors; no stack traces in prod |
| V7 Logging | Audit trail | Immutable AuditLog entries for auth, admin, billing events |
| V8 Data Protection | Secrets management | Environment variables only; no secrets in source |
| V9 Communications | TLS | Enforced at nginx in production (HSTS header) |
| V10 Code Integrity | Dependency scanning | pip-audit + npm audit in CI; Bandit SAST |
| V11 Business Logic | Quota enforcement | Redis daily prediction counter; plan entitlement matrix |
| V12 File Handling | Upload restrictions | 50 MB cap; CSV schema validation; MinIO object isolation |
| V13 API | Rate limiting | Per-user sliding window; per-API-key daily quota; 429 Retry-After |
| V14 Configuration | Security headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy via Nginx |

### Known Trade-offs
- Color-contrast in dark theme was not automatically verified by CI (axe-core skips it in JSDOM). Manual review required.
- CSP `unsafe-inline` is required for Vite dev HMR; tighten with nonces in production builds.
- HSTS is commented out in the dev nginx config — enable it in the production nginx overlay.
