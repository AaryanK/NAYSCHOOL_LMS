# Anthology/Blackboard REST API Integration Plan

This plan details the steps and security compliance guidelines required to turn the Blackboard connector into a live production sync service.

---

## Production Security & Privacy Checklist

Any production-level connection to an institution's Blackboard instance must strictly comply with the following 10 rules:

1. **Anthology Developer Registration**: Register the application in the [Anthology Developer Portal](https://developer.anthology.com) to generate application credentials.
2. **App Credentials**: Safely obtain the Application ID, Client ID (OAuth Key), and Client Secret.
3. **Institutional Administrator Approval**: Request a university Blackboard Administrator to authorize and install the App ID in their instance panel (**System Admin** > **REST API Integrations**).
4. **Least Privilege (Read-only)**: Request read-only access scopes first (to sync courses, announcements, content, and assignments) before asking for write or grade book privileges.
5. **No Password Scraping**: Never ask for or store student passwords. All REST transactions must rely strictly on standard OAuth2 code grant tokens.
6. **Encrypted Token Storage**: Store all access and refresh tokens encrypted in the database (e.g. using Fernet symmetric encryption via the Token Service).
7. **Minimal Data Collection**: Pull only the courses, assignments, and announcements required to populate the NaySchool workspace. Do not sync student directory info unless requested.
8. **FERPA/Privacy Compliance**: Respect student privacy and do not train AI models on student educational records or content without explicit student/institution consent.
9. **Security Audits**: Log all sync runs, data modifications, and API calls to `LMSSyncLog` for audit security reviews.
10. **Pilot Test Strategy**: Run pilot tests with a single institution and a limited course sandbox before rolling out institution-wide.

---

## 1. Anthology Developer Portal App Registration
To query a university's Blackboard instance, we must register as a developer:
1. Visit the [Anthology Developer Portal](https://developer.anthology.com).
2. Create an account and register a new REST API application.
3. This generates:
   - **Application ID** (used by the university admin to authorize permissions).
   - **OAuth Key** (Client ID).
   - **OAuth Secret** (Client Secret).

## 2. University Administrator Authorization
University Blackboard administrators hold complete control over REST integrations:
1. The administrator must log into their Blackboard Learn instance as System Administrator.
2. Navigate to **System Admin** > **REST API Integrations**.
3. Select **Register Integration**.
4. Enter the **Application ID** generated in Step 1.
5. Choose a dedicated system user (we recommend setting up a virtual "NaySchool Sync Service" user).
6. Set permissions:
   - We recommend requesting **Read-only** scopes first (read course registries, student enrollments, course content, and due dates).
   - Avoid requesting write access or grades-modification scopes unless requested by instructors.

## 3. Secure OAuth 2.0 Authorization Flow
To authenticate a student's Blackboard account:
1. Redirect the student to the university's Blackboard login portal (`https://{school-domain}/learn/api/public/v1/oauth2/authorizationcode`).
2. Upon user login, Blackboard redirects back with a temporary authorization code.
3. The backend exchanges the code, client ID, and client secret for an access token and refresh token:
   ```bash
   POST https://{school-domain}/learn/api/public/v1/oauth2/token
   ```
4. Tokens must be stored securely (see `docs/SECURITY_AND_PRIVACY.md` for encryption guidelines).

## 4. REST API Endpoint Mapping
Once connected, implement the following queries in `backend/lms/providers/blackboard.py`:
- **Courses**:
  - Endpoint: `GET /learn/api/public/v3/courses` (filter by user enrollment).
- **Course Content / Syllabus**:
  - Endpoint: `GET /learn/api/public/v1/courses/{courseId}/contents`.
- **Assessments / Assignments**:
  - Endpoint: `GET /learn/api/public/v1/courses/{courseId}/gradebook/columns`.
- **Announcements**:
  - Endpoint: `GET /learn/api/public/v1/courses/{courseId}/announcements`.
- **Grades**:
  - Endpoint: `GET /learn/api/public/v2/courses/{courseId}/gradebook/users/me`.

