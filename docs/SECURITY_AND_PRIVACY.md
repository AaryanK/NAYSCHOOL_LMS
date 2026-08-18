# Security and Privacy Guidelines

This document outlines the safety measures implemented in NaySchool 3.0 and compliance requirements prior to school production deployments.

---

## 1. Local Configuration Isolation
- Under no circumstances should the `.env` configuration file containing real API credentials or database keys be committed to Git.
- A template `.env.example` file is provided to document parameters safely.
- The project `.gitignore` explicitly excludes `.env` and SQLite database (`*.db`) files.

## 2. Password Hashing
- Student credentials must never be stored in plain text.
- NaySchool 3.0 uses **Passlib** with **Bcrypt** password hashing:
  - Hashing runs dynamically during registration (`POST /api/auth/register`).
  - Hashing utilizes cryptographic salts to prevent pre-computation attacks.

## 3. LMS OAuth Token Encryption
- **Symmetric Encryption**: LMS credentials (access and refresh tokens) are highly sensitive. They must never be stored in plain text.
- **Fernet Encryption**: Tokens are encrypted using Fernet symmetric encryption prior to database writes. The encryption key `TOKEN_ENCRYPTION_KEY` is loaded from the environment settings.
- **Exclusion of Secrets**: API endpoints that expose `LMSConnection` details explicitly omit raw access/refresh tokens from responses to prevent accidental token exposure.

## 4. Student Educational Material Privacy (RAG & Chunks)
Uploaded lecture notes, homework guidelines, and syllabus documents constitute sensitive educational materials and may contain student educational records:
- **No Cross-User Leakage**: Search and chunks retrieval queries strictly check course ownership. The course ownership verification in `POST /api/courses/{course_id}/search` and `GET /api/courses/{course_id}/chunks` queries validates that only the student registered to that course can query or list chunks. No student can access chunks belonging to another user.
- **LLM Privacy**: The AI provider plan specifies how and when context is sent. When querying cloud models, chunks are transmitted as prompts. Consent checks should be enabled in production.

## 5. Ingestion Processing Safety & Sanitization
- **Error Log Safety**: Ingestion processing errors (captured during background extraction or embedding generation) are saved on the `CourseFile` record. The ingestion worker ensures that raw stack traces containing configuration secrets, passwords, or environment paths are sanitized and NEVER exposed to frontend endpoints or logs.
- **Malware Scanning (Roadmap)**: In production environments, all uploaded file streams must be routed through scanner engines (e.g., ClamAV) prior to extraction or local filesystem storage to prevent script injection or Trojan exploits.

## 6. Audit Logging & Compliance
- **Audit Logs**: Critical student actions (uploads, logins, reprocessing, LLM tutor concept checks) generate immutable audit logs capturing timestamps, user identifiers, and action types for security reviews.
- **Multi-Tenant Isolation**: Institutional deployments should partition databases or schemas by school/district. Each tenant uses unique encryption keys to maintain strict administrative borders.

## 7. HTTPS (TLS/SSL) Deployment
- Ensure that the application runs behind a reverse proxy (e.g. Nginx, Caddy) that enforces **HTTPS** in production.
- Session JWT tokens must be transmitted securely over TLS headers.

## 8. FERPA and Academic Integrity Compliance
- **FERPA Compliance**: Prior to deploying at educational institutions, ensure student directory information is protected. Consent must be explicitly checked before sharing data with third-party LLM providers.
- **Student Mastery & Attempts Privacy**: Student mastery scores, weakness lists, practice quiz history, and auto-generated study tasks are sensitive educational records.
  - Mastery dashboards must only be accessible to the authenticated owner.
  - Analytics and performance dashboards must respect privacy settings and must not be shared or leaked across accounts.
  - Future instructor dashboards must secure explicit student consent prior to displaying detailed individual learning statistics.
- **Academic Integrity**: The system incorporates a dedicated **IntegrityAgent** that analyzes student requests. Cheating queries, live exams, and copy-paste exam prompts are flagged and blocked, suggesting constructive study alternatives instead of solutions.
- **No Training on LMS Data**: NaySchool does not train machine learning models on synchronized student records, grades, or materials without explicit institutional consent.
- **Data Deletion & Export**: Deleting an integration connection or mapped course immediately purges all sync histories, logs, and linked assignments. Future releases will support complete user profile export utilities to maintain data self-sovereignty.

## 9. Study Activity & Streak Privacy (Phase 6A)
- **Activity Logging Scope**: `StudyActivity` records capture only the activity type (e.g., `tutor_question`, `practice_attempt`) and timestamps. No question content, answer text, or document data is stored in activity records.
- **Owner-Only Access**: Activity feeds and streak endpoints (`GET /api/me/activity`, `GET /api/me/streak`) are authenticated and scoped strictly to the requesting user. No cross-user activity visibility exists.
- **Streak Computation**: Streak calculations are derived server-side from activity timestamps. No external services or analytics platforms are contacted.

## 10. Usage Tracking & Plan Scaffold Privacy (Phase 6A)
- **Usage Counters**: `UsageCounter` records track monthly aggregate counts (tutor questions, uploads, practice generations, exam prep generations) per user. Individual request payloads are NOT stored in usage counters.
- **Plan Assignment**: The `User.plan` field defaults to `free`. The dev-only override endpoint (`PATCH /api/me/plan-dev`) is intended exclusively for local testing and must be disabled or removed before production deployment.
- **No Payment Data**: NaySchool does not collect, store, or process any payment information (credit cards, bank details, billing addresses). The plan scaffold is purely functional. Future Stripe integration will delegate all payment handling to Stripe's PCI-compliant infrastructure.

## 11. Notification Privacy (Phase 6A)
- **User-Scoped Notifications**: All notification queries filter by `user_id`. A student can only view, generate, and mark-as-read their own notifications.
- **No External Delivery**: Notifications are currently in-app only. No email, SMS, or push notification systems are active. When external delivery is implemented, explicit user consent and opt-out mechanisms must be provided.
- **Deduplication**: The reminder generation system checks for existing notifications before creating new ones, preventing notification spam.

## 12. Onboarding Data Privacy (Phase 6A)
- **Voluntary Disclosure**: All onboarding profile fields (education level, major, school name, study goal, daily study minutes, preferred study style) are optional and voluntarily provided by the student.
- **No External Sharing**: Profile data is used exclusively to personalize the student's learning experience within NaySchool. It is not shared with LLM providers, LMS connectors, or any third-party service.
- **Deletion**: Deleting a user account cascades to delete `UserProfile`, `StudyActivity`, `UsageCounter`, and `Notification` records via database-level `CASCADE` constraints.


