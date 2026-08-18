# Blackboard Learn Integration

## Verified OAuth contract

This implementation follows Blackboard's current official Three-Legged OAuth documentation:

- Authorization: `GET {institution-origin}/learn/api/public/v1/oauth2/authorizationcode`
- Token and refresh: `POST {institution-origin}/learn/api/public/v1/oauth2/token`
- `client_id` is the Developer Portal **OAuth Key**, not the **Application ID**.
- Default scope is `read offline`: `read` allows student-scoped reads and `offline` enables refresh tokens.
- PKCE uses a random verifier and the only documented challenge method, `S256`.

Official references:

- https://docs.blackboard.com/docs/blackboard/rest-apis/getting-started/3lo
- https://docs.blackboard.com/docs/blackboard/rest-apis/start-here

## Security model

NaySchool never receives a student's Blackboard password. The student enters only the origin of their institution's Blackboard site, then authenticates and grants access on that institution's Learn page.

Each connection stores its canonical institution origin. The server rejects origins containing credentials, paths, queries, or fragments; production accepts HTTPS only and rejects localhost and non-public IP literals.

Every authorization attempt stores a hash of a cryptographically random state value in `lms_oauth_states`. The transaction binds the state to the NaySchool user, provider, connection, encrypted PKCE verifier, expiry, and one-time consumption timestamp. Raw state values are not stored.

Access tokens, refresh tokens, and PKCE verifiers are encrypted with Fernet. `TOKEN_ENCRYPTION_KEY` is mandatory outside development/test/local environments. Tokens are never returned through API response models or frontend code.

## Developer Portal setup

The NaySchool application owner must create one REST application in the Anthology Developer Portal and configure:

1. Application name and description for NaySchool.
2. Redirect URI exactly matching `BLACKBOARD_REDIRECT_URI`.
3. The generated OAuth Key as `BLACKBOARD_CLIENT_ID`.
4. The generated OAuth Secret as `BLACKBOARD_CLIENT_SECRET`.
5. The generated Application ID as `BLACKBOARD_APP_ID` for institutional installation records.

The application owner—not each institution—owns the production Developer Portal application and any rate/site limit requests.

## Institution administrator setup

The Blackboard administrator must open **System Admin → REST API Integrations → Create Integration**, enter NaySchool's `BLACKBOARD_APP_ID`, enable the integration, and authorize the least-privilege access required for student-scoped read operations. The administrator must also ensure the institution's custom login/SSO page permits the Learn 3LO authorization flow.

The student enters the institution-specific Blackboard origin on `/lms`; it is not a global server setting.

## Implemented phase

- Real public 3LO endpoints, opaque persistent state, one-time expiry checks, S256 PKCE, encrypted token storage, refresh support, sanitized OAuth errors, callback redirect, and authenticated connection probe.
- Production mock success has been removed. Course, assignment, and content synchronization currently fail explicitly until their real endpoint phase is implemented and verified against a connected institution.

## External verification requirement

Automated tests mock Blackboard HTTP responses and cannot prove that an institution has installed the Application ID or grants the needed privileges. A real connection requires Developer Portal credentials, an administrator-approved REST integration, a reachable Blackboard Learn SaaS origin, and a student account at that institution.
