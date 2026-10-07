# AgriScope API Reference

Comprehensive reference for the AgriScope REST API (`/api/v1`).

---

## 1. Global Standards & Conventions

- **Base URL Prefix**: `/api/v1`
- **Protocol**: HTTP/1.1 and HTTP/2 over TLS
- **Encoding**: UTF-8, `Content-Type: application/json`
- **Correlation ID**: Every request receives a unique UUID in `X-Request-ID`. If supplied in client request headers, it is preserved; otherwise, generated automatically.
- **Consistent Error Structure**:
  ```json
  {
    "detail": "Descriptive human-readable explanation of error",
    "code": "ERROR_CODE_STRING",
    "request_id": "c1f729e2-2a5c-44d7-8e6d-6258f7004491"
  }
  ```

### Authentication Architecture
- **Access Tokens**: Short-lived (15 minutes) RS256/HS256 JSON Web Tokens transmitted in HTTP header `Authorization: Bearer <token>`.
- **Refresh Tokens**: Long-lived (7 days) cryptographically random hex tokens stored exclusively in `httpOnly`, `Secure`, `SameSite=Lax` cookies named `refresh_token`. Protected by single-use token family rotation and reuse detection.

---

## 2. Authentication Endpoints (`/api/v1/auth`)

### Register
- **Endpoint**: `POST /api/v1/auth/register`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!",
    "name": "Jane Doe"
  }
  ```
- **Password Rules**: Minimum 8 characters, at least 1 uppercase letter, at least 1 digit, checked against common/breached passwords.
- **Response**: `201 Created`
  ```json
  {
    "id": "uuid",
    "email": "user@example.com",
    "name": "Jane Doe",
    "role": "farmer",
    "plan": "free",
    "status": "pending_verification",
    "email_verified": false
  }
  ```

### Login
- **Endpoint**: `POST /api/v1/auth/login`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPassword123!",
    "totp_code": "123456",        // Optional: required if 2FA enabled
    "recovery_code": "A1B2-C3D4"  // Optional: alternative to totp_code
  }
  ```
- **Responses**:
  - `200 OK`: Successful login. Sets `refresh_token` httpOnly cookie.
    ```json
    {
      "access_token": "eyJhbGciOi...",
      "token_type": "bearer",
      "user": { ... }
    }
    ```
  - `401 Unauthorized` (`2FA_REQUIRED:<temp_token>`): When 2FA is active and neither code was provided.
    ```json
    {
      "detail": "2FA_REQUIRED:eyJhbGciOi...",
      "code": "2FA_REQUIRED",
      "request_id": "uuid"
    }
    ```
  - `423 Locked`: Account locked after 5 consecutive failed attempts (15 min auto-unlock).

### Token Refresh
- **Endpoint**: `POST /api/v1/auth/refresh`
- **Auth**: Cookie-based (`refresh_token` httpOnly cookie)
- **Response**: `200 OK`. Sets new rotated `refresh_token` cookie.
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```
- **Security**: If an already rotated token is re-presented, all sessions in the token family are immediately revoked (replay attack defense).

### Logout
- **Endpoint**: `POST /api/v1/auth/logout`
- **Auth**: Cookie-based (`refresh_token` httpOnly cookie)
- **Response**: `200 OK`. Revokes the current session and clears the cookie.

### Logout All
- **Endpoint**: `POST /api/v1/auth/logout-all`
- **Auth**: Bearer Token
- **Response**: `200 OK`. Revokes all active sessions for the user.

### List Sessions
- **Endpoint**: `GET /api/v1/auth/sessions`
- **Auth**: Bearer Token
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "uuid",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0 ...",
      "created_at": "2026-10-07T00:00:00Z",
      "expires_at": "2026-10-14T00:00:00Z",
      "is_current": true
    }
  ]
  ```

### Revoke Session
- **Endpoint**: `DELETE /api/v1/auth/sessions/{session_id}`
- **Auth**: Bearer Token
- **Response**: `204 No Content`

### Email Verification
- **Endpoint**: `POST /api/v1/auth/verify-email`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "token": "signed-verification-token"
  }
  ```
- **Response**: `200 OK`

### Resend Verification Email
- **Endpoint**: `POST /api/v1/auth/resend-verification`
- **Auth**: Public (Rate-limited)
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**: `200 OK` (Constant response regardless of email existence)

### Forgot Password
- **Endpoint**: `POST /api/v1/auth/forgot-password`
- **Auth**: Public (Rate-limited)
- **Request Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**: `200 OK` (Constant response to prevent email enumeration)

### Reset Password
- **Endpoint**: `POST /api/v1/auth/reset-password`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "token": "one-time-password-reset-token",
    "new_password": "NewSecurePassword456!"
  }
  ```
- **Response**: `200 OK`. Revokes all active user sessions across all devices.

---

## 3. User & Entitlement Endpoints (`/api/v1/users`)

### Get Entitlements & Daily Quota
- **Endpoint**: `GET /api/v1/users/me/entitlements`
- **Auth**: Bearer Token
- **Response**: `200 OK`
  ```json
  {
    "plan": "free",
    "daily_prediction_limit": 10,
    "predictions_used_today": 3,
    "predictions_remaining_today": 7,
    "features": {
      "manual_et": true,
      "location_weather": true,
      "single_field": true,
      "basic_crops": true,
      "export_csv": true,
      "satellite_indices": false,
      "sentinel_pipeline": false,
      "custom_kc": false,
      "advanced_crops": false,
      "export_geojson": false,
      "pdf_report": false,
      "api_access": false,
      "unlimited_fields": false,
      "priority_inference": false
    }
  }
  ```

### Get Current User Profile
- **Endpoint**: `GET /api/v1/users/me`
- **Auth**: Bearer Token
- **Response**: `200 OK` with full user profile details.

### Update Profile
- **Endpoint**: `PATCH /api/v1/users/me/profile`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "name": "Jane Smith"
  }
  ```
- **Response**: `200 OK`

### Initiate Email Change
- **Endpoint**: `POST /api/v1/users/me/change-email`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "new_email": "newjane@example.com",
    "password": "CurrentPassword123!"
  }
  ```
- **Response**: `200 OK`. Dispatches verification link to new email address.

### Confirm Email Change
- **Endpoint**: `POST /api/v1/users/me/confirm-email-change`
- **Auth**: Public
- **Request Body**:
  ```json
  {
    "token": "signed-email-change-token"
  }
  ```
- **Response**: `200 OK`. Updates email and marks email verified.

### Change Password
- **Endpoint**: `POST /api/v1/users/me/change-password`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "current_password": "CurrentPassword123!",
    "new_password": "NewSecurePassword789!"
  }
  ```
- **Response**: `200 OK`. Revokes all sessions on other devices.

### Setup TOTP 2FA
- **Endpoint**: `POST /api/v1/users/me/2fa/setup`
- **Auth**: Bearer Token
- **Response**: `200 OK`
  ```json
  {
    "secret": "JBSWY3DPEHPK3PXP",
    "provisioning_uri": "otpauth://totp/AgriScope:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=AgriScope",
    "qr_code_base64": "data:image/png;base64,iVBORw0KGgo..."
  }
  ```

### Verify & Enable TOTP 2FA
- **Endpoint**: `POST /api/v1/users/me/2fa/verify`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "code": "123456"
  }
  ```
- **Response**: `200 OK`. Returns single-use plaintext recovery codes (stored hashed in database).
  ```json
  {
    "enabled": true,
    "recovery_codes": [
      "ABCD-EFGH",
      "IJKL-MNOP",
      "QRST-UVWX",
      "YZ12-3456",
      "7890-ABCD",
      "EFGH-IJKL",
      "MNOP-QRST",
      "UVWX-YZ12"
    ]
  }
  ```

### Disable TOTP 2FA
- **Endpoint**: `POST /api/v1/users/me/2fa/disable`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "password": "CurrentPassword123!",
    "code": "123456" // or recovery code
  }
  ```
- **Response**: `200 OK`

### Export Account Data (GDPR)
- **Endpoint**: `GET /api/v1/users/me/export`
- **Auth**: Bearer Token
- **Response**: `200 OK`
  ```json
  {
    "user": { ... },
    "sessions": [ ... ],
    "audit_logs": [ ... ],
    "fields": [],
    "predictions": []
  }
  ```

### Soft Delete Account
- **Endpoint**: `DELETE /api/v1/users/me`
- **Auth**: Bearer Token
- **Request Body**:
  ```json
  {
    "password": "CurrentPassword123!"
  }
  ```
- **Response**: `200 OK`. Sets user status to `deleted`, revokes all sessions, and schedules purge.

### User Audit Trail
- **Endpoint**: `GET /api/v1/users/me/audit`
- **Auth**: Bearer Token
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "uuid",
      "actor": "user@example.com",
      "action": "auth.login",
      "target": "user@example.com",
      "metadata": { "client_ip": "127.0.0.1" },
      "timestamp": "2026-10-07T02:00:00Z"
    }
  ]
  ```

---

## 4. Public Researcher API (`/api/v1/public`)

Programmatic REST access designed for agronomists, remote-sensing data pipelines, and research institutes. Requires an active API key generated in the AgriScope dashboard (`Settings > API Keys`).

### Authentication & Rate Limits
- **Header**: `X-API-Key: agri_live_<secret_token>`
- **Rate Limit**: 60 requests/minute by default (`429 Too Many Requests` with `Retry-After` header).
- **Daily Quota**: 5,000 requests/day per key.

### Public Single Inference
- **Endpoint**: `POST /api/v1/public/predict`
- **Scope Required**: `predict:read`
- **Request Body**:
  ```json
  {
    "temp_max": 34.5,
    "temp_min": 21.0,
    "humidity": 55.0,
    "wind_speed": 2.4,
    "solar_radiation": 22.0
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "et0": 5.42,
    "confidence_interval": {
      "lower": 5.12,
      "upper": 5.72,
      "coverage": 0.90
    },
    "model_version": "v1.0.0-random_forest",
    "algorithm": "random_forest",
    "reference_fao56": 5.38,
    "source": "api"
  }
  ```

### Curl Example
```bash
curl -X POST https://api.agriscope.local/api/v1/public/predict \
  -H "X-API-Key: agri_live_abcdef1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "temp_max": 33.0,
    "temp_min": 20.5,
    "humidity": 45.0,
    "wind_speed": 2.1
  }'
```

### Python Example
```python
import httpx

client = httpx.Client(
    base_url="https://api.agriscope.local/api/v1/public",
    headers={"X-API-Key": "agri_live_abcdef1234567890"}
)

response = client.post("/predict", json={
    "temp_max": 33.0,
    "temp_min": 20.5,
    "humidity": 45.0,
    "wind_speed": 2.1
})
print("Predicted ET0 (mm/day):", response.json()["et0"])
```

### Public Batch Job Submission
- **Endpoint**: `POST /api/v1/public/batch/submit`
- **Scope Required**: `batch:write`
- **Multipart Form**: Upload `.csv` file with column headers `temp_max, temp_min, humidity, wind_speed`.

### Public Batch Job Status
- **Endpoint**: `GET /api/v1/public/batch/status/{job_id}`
- **Scope Required**: `batch:write` or `predict:read`

### Public Weather Prefill
- **Endpoint**: `GET /api/v1/public/weather/prefill?latitude=36.7&longitude=3.05&target_date=2026-10-07`
- **Scope Required**: `weather:read`

### Public Field ET Time Series
- **Endpoint**: `GET /api/v1/public/fields/{field_id}/et-series?start_date=2026-09-01&end_date=2026-10-01`
- **Scope Required**: `fields:read`

---

## 5. Billing & Subscription Endpoints (`/api/v1/billing`)

- `GET /api/v1/billing/subscription`: Current plan, Stripe subscription status, and billing cycle.
- `POST /api/v1/billing/checkout`: Create Stripe Checkout Session (`{ "plan": "pro" }`).
- `POST /api/v1/billing/portal`: Create Stripe Customer Billing Portal Session.
- `POST /api/v1/billing/webhook`: Stripe webhook handler (verifies `Stripe-Signature` and dispatches idempotent subscription state transitions).
- `POST /api/v1/billing/mock/upgrade` & `POST /api/v1/billing/mock/downgrade`: Local/testing plan transitions.

