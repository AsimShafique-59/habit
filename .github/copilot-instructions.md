# Habit Tracker — Copilot Instructions

## Project Overview

Cross-platform mobile habit-tracking application (iOS + Android) with a Django REST Framework backend. The system enables users to build positive habits, eliminate negative habits, and consume short-form motivational content.

**SRS Version:** 1.0 | **Status:** Baseline — Implementation Ready  
**All API endpoints prefixed:** `/api/v1`  
**Auth:** `Authorization: Bearer <access_token>` on all authenticated endpoints  
**Timestamps:** ISO 8601 UTC throughout

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django + Django REST Framework |
| Auth | JWT (access TTL: 1h, refresh TTL: 30 days, rotation on use) |
| Database | PostgreSQL (relational) + TimescaleDB/ClickHouse (time-series analytics) |
| Storage | S3-compatible object storage + CDN |
| Push | APNs (iOS) + FCM (Android) |
| AI | LLM provider (OpenAI-compatible), archetype-cached |
| Mobile | iOS 16+ / Android 10+ |

---

## Sprint Plan (16 sprints × 2 weeks)

| Sprint | Theme | Modules |
|---|---|---|
| 1–2 | Foundation | Infra, Auth, User Profile |
| 3–4 | Core Tracking | Habit Management, Sync, Offline |
| 5 | AI Onboarding | AI Habit Generation |
| 6 | Integrations | Apple Health, Google Fit, Calendar |
| 7–8 | Reporting | Analytics pipeline + 15 reports |
| 9 | Notifications | Reminders + smart suppression |
| 10–11 | Motivation | Bad-habit programs, Urge SOS |
| 12 | Daily Insight | Content feed, audio playback |
| 13 | Reflection | Journaling, mood tracking |
| 14 | Wearables & Widgets | watchOS, Wear OS, widgets |
| 15 | Subscription & Admin | Billing, content CMS |
| 16 | Hardening | Performance, security, polish |

---

## Module Index

1. [Infrastructure & DevOps](#1-infrastructure--devops)
2. [Authentication & User Account](#2-authentication--user-account)
3. [Habit Management](#3-habit-management)
4. [AI Habit Generation](#4-ai-habit-generation)
5. [Reporting & Analytics](#5-reporting--analytics)
6. [Notifications & Reminders](#6-notifications--reminders)
7. [Motivation / Bad-Habit Removal](#7-motivation--bad-habit-removal)
8. [Daily Insight](#8-daily-insight)
9. [Reflection & Journaling](#9-reflection--journaling)
10. [Integrations](#10-integrations)
11. [Wearables & Widgets](#11-wearables--widgets)
12. [Subscription & Billing](#12-subscription--billing)
13. [Admin / Content Curator](#13-admin--content-curator)

---

## 1. Infrastructure & DevOps

### INFRA-001 — Cloud environment & CI/CD pipeline
**Priority:** H | **Sprint:** 1 | **Type:** DevOps

- Three isolated environments (dev / staging / prod) with separate credentials
- Backend deploys via container registry; rolling deploys with zero downtime
- Mobile builds on every PR; signed builds to TestFlight and Play Internal Testing on merge to main
- Secrets in secret manager (not env files); Infrastructure-as-Code in repo
- **Edge Cases:** Failed deploy → auto-rollback; migrations run pre-deploy with rollback scripts

### INFRA-002 — Database schema baseline & migrations
**Priority:** H | **Sprint:** 1 | **Dependencies:** INFRA-001 | **Type:** Backend

Core tables: `users`, `habits`, `habit_completions`, `streaks`, `notifications`, `journal_entries`, `programs`, `program_enrollments`, `daily_insights`, `subscriptions`

- All migrations versioned, reversible, idempotent
- Audit columns (`created_at`, `updated_at`, `deleted_at`) on every table
- Indexes on: `user_id` FKs, `habit_completions(user_id, completion_date)`, `journal_entries(user_id, entry_date)`
- Soft-delete via `deleted_at` on user-owned tables

### INFRA-003 — Time-series store for analytics
**Priority:** H | **Sprint:** 2 | **Dependencies:** INFRA-001 | **Type:** Backend

- Ingestion endpoint: batched events with `user_id`, `event_type`, `event_timestamp`, `payload` (JSON)
- Pre-aggregation jobs: hourly + daily
- Retention policy: raw events purged af      ter 24 months

### INFRA-004 — Object storage + CDN
**Priority:** H | **Sprint:** 1 | **Dependencies:** INFRA-001 | **Type:** DevOps

- Folder structure: `daily-insights/`, `programs/{program_id}/audio/`, `user-uploads/{user_id}/`
- Public CDN URLs for curated content; signed URLs for user uploads
- Lifecycle: user uploads → cold storage after 90 days of inactivity; antivirus on upload pipeline

### INFRA-005 — Logging, monitoring, alerting
**Priority:** H | **Sprint:** 2 | **Dependencies:** INFRA-001 | **Type:** DevOps

- Structured JSON logs with `trace_id`, `user_id`, `request_id`
- Dashboards: API latency p50/p95/p99, error rate, DB pool usage
- Alerts: error rate > 1% for 5 min; p95 latency > 2s for 5 min; queue backlog > threshold

---

## 2. Authentication & User Account

### AUTH-001 — Email/password sign-up
**Priority:** H | **Sprint:** 1 | **Type:** Full-stack

```
POST /auth/signup/email  (Public)

Request:
{
  "email": "string",         // RFC 5322, max 255, unique case-insensitive
  "password": "string",      // min 8, upper+lower+digit, max 128
  "name": "string",          // 1-80 chars, trimmed
  "locale": "string",        // BCP 47; default en-US
  "timezone": "string",      // IANA; default UTC
  "accepted_tos_version": "string"  // required, must match published version
}

Response 201:
{
  "user_id": "uuid",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "email_verified": false
}
```

- Duplicate email → 409 `EMAIL_TAKEN`
- Disposable email → 422 `DISPOSABLE_EMAIL`
- Rate limit: 5 attempts/IP/hour
- Password: Argon2id or bcrypt (cost ≥ 12)
- Verification email within 30s; audit log written

### AUTH-002 — Apple Sign-In
**Priority:** H | **Sprint:** 1 | **Type:** Full-stack

```
POST /auth/signin/apple  (Public)

Request:
{
  "identity_token": "string",
  "authorization_code": "string",
  "name": "string",      // optional, first sign-in only
  "locale": "string",
  "timezone": "string"
}

Response 200:
{
  "user_id": "uuid",
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "is_new_user": true
}
```

- Validate `identity_token` against Apple's public keys; verify `aud`, `iss`, `exp`
- Private relay email: store as-is, treat as verified
- Account linking by email requires explicit user confirmation

### AUTH-003 — Google Sign-In
**Priority:** H | **Sprint:** 1 | **Type:** Full-stack

```
POST /auth/signin/google  (Public)
// Same response shape as AUTH-002
// Validate id_token against Google public keys; verify aud matches client ID
```

### AUTH-004 — Email/password login
**Priority:** H | **Sprint:** 1 | **Dependencies:** AUTH-001 | **Type:** Backend

```
POST /auth/login  (Public)

Request: { "email": "string", "password": "string" }
Response 200: { "user_id": "uuid", "access_token": "string", "refresh_token": "string", "expires_in": 3600 }
```

- Invalid credentials → 401 `INVALID_CREDENTIALS` (never disclose whether email exists)
- 5 failed attempts in 15 min → 15-min lock + email alert
- Soft-deleted account → 403 `ACCOUNT_DEACTIVATED`

### AUTH-005 — Token refresh
**Priority:** H | **Sprint:** 1 | **Type:** Backend

```
POST /auth/refresh
Request: { "refresh_token": "string" }
Response 200: new token pair
```

- Reused rotated token → revoke entire token family + force re-login
- Expired → 401 `REFRESH_EXPIRED`
- Access TTL: 1h; Refresh TTL: 30 days

### AUTH-006 — Logout
**Priority:** H | **Sprint:** 1 | **Type:** Backend

```
POST /auth/logout  (Auth required)
Request: { "all_sessions": false }
Response: 204 No Content
```

### AUTH-007 — Email verification
**Priority:** H | **Sprint:** 1 | **Type:** Full-stack

```
GET /auth/verify-email?token={token}
// Token TTL: 24h, single-use
// Success → redirect to deep link app://email-verified
// Already verified → idempotent success
```

### AUTH-008 — Password reset
**Priority:** H | **Sprint:** 2 | **Type:** Full-stack

```
POST /auth/password-reset/request   body: { "email": "string" }  → 204 (always)
POST /auth/password-reset/complete  body: { "token": "string", "new_password": "string" }
```

- Token TTL: 1h, single-use
- All active sessions revoked on successful reset
- Never disclose whether email exists

### AUTH-009 — Get / update user profile
**Priority:** H | **Sprint:** 2 | **Type:** Full-stack

```
GET  /users/me
PATCH /users/me

Editable: name, locale, timezone, identity_tags[], notification_quiet_hours, theme_preference
Read-only: user_id, email, created_at, email_verified, subscription_tier

Validation:
  identity_tags: max 10, each 1-40 chars
  notification_quiet_hours: { "start": "HH:MM", "end": "HH:MM" }
  theme_preference: light | dark | system
```

### AUTH-010 — Account deletion (GDPR)
**Priority:** H | **Sprint:** 2 | **Type:** Full-stack

```
POST /users/me/delete          body: { "password": "string", "reason": "string?" }
POST /users/me/delete/cancel   // cancel within 30-day grace period
```

- Soft-delete on request; hard-delete after 30 days (purges all PII)
- Anonymized analytics retained
- Active subscription → block or cancel first (configurable)

### AUTH-011 — Data export (GDPR portability)
**Priority:** M | **Sprint:** 2 | **Type:** Backend

```
POST /users/me/export           → 202 { "export_id": "uuid" }
GET  /users/me/export/{export_id}
→ { "export_id": "uuid", "status": "pending|processing|ready|failed", "download_url": "string?", "expires_at": "iso" }
```

- Includes habits, completions, journals, mood logs, uploads, program enrollments
- Signed URL valid 24h

---

## 3. Habit Management

### HM-001 — Create habit
**Priority:** H | **Sprint:** 3 | **Type:** Full-stack

```
POST /habits  (Auth required)

Request:
{
  "title": "string",               // 1-80 chars
  "description": "string?",
  "category": "Health|Fitness|Mindfulness|Productivity|Learning|Finance|Relationships|Other",
  "icon": "string",
  "color_hex": "string",           // valid #RRGGBB
  "frequency_type": "daily|weekdays|n_per_week",
  "frequency_days": [1,2,3,4,5],  // ISO weekday 1=Mon..7=Sun
  "frequency_count": 3,            // 1-7 for n_per_week
  "quantity_target": 8,            // positive, ≤ 99999
  "quantity_unit": "glasses",
  "duration_minutes": 30,
  "time_window_start": "06:00",    // HH:MM, must be < time_window_end
  "time_window_end": "10:00",
  "identity_tags": ["runner"],     // max 5
  "difficulty": "tiny|small|medium",
  "anchor_habit_id": "uuid?",      // must be user's own, not archived
  "reminder_times": ["07:30"],     // max 3, HH:MM
  "is_quit_habit": false
}

Response 201:
{ "habit_id": "uuid", "user_id": "uuid", ...all fields..., "current_streak": 0, "longest_streak": 0, "created_at": "iso" }
```

- Free tier at habit limit → 403 `TIER_LIMIT_REACHED`
- Self-anchoring not allowed
- Anchor habit deleted later → habit becomes unanchored (not deleted)

### HM-002 — List habits
**Priority:** H | **Sprint:** 3 | **Type:** Backend

```
GET /habits?status=active|archived|all&category=&is_quit_habit=&cursor=&limit=50&sort=created_at_desc|title_asc|streak_desc

Response 200: { "items": [...], "next_cursor": "string?", "total": 12 }
```

### HM-003 — Get habit by ID
**Priority:** H | **Sprint:** 3 | **Type:** Backend

```
GET /habits/{habit_id}
// Returns habit + completions_last_30_days: [{ "date": "YYYY-MM-DD", "quantity": 1, "completed_at": "iso" }]
// Owned by another user → 404 (never 403, prevents enumeration)
```

### HM-004 — Update habit
**Priority:** H | **Sprint:** 3 | **Type:** Backend

```
PATCH /habits/{habit_id}
// All fields from HM-001 except is_quit_habit (immutable)
// Use If-Match header with updated_at for optimistic locking; 409 on conflict
// Frequency change: recalculates streak from change date, not retroactive
```

### HM-005 — Archive / unarchive habit
**Priority:** H | **Sprint:** 3 | **Type:** Backend

```
POST /habits/{habit_id}/archive
POST /habits/{habit_id}/unarchive
// Reminders cancelled on archive; completions preserved; attempt to complete archived → 409
```

### HM-006 — Delete habit (hard)
**Priority:** M | **Sprint:** 3 | **Type:** Backend

```
DELETE /habits/{habit_id}?confirm=true
// Response: 204; anchored habits become unanchored
```

### HM-007 — Mark habit complete
**Priority:** H | **Sprint:** 3 | **Type:** Full-stack

```
POST /habits/{habit_id}/completions

Request:
{
  "completion_date": "YYYY-MM-DD",  // max 7 days past, not future (user TZ)
  "quantity": 8,                    // ≤ quantity_target * 2
  "completed_at": "iso",
  "source": "manual|auto_health|widget|watch|shortcut"
}

Response 200/201:
{
  "completion_id": "uuid",
  "habit_id": "uuid",
  "completion_date": "YYYY-MM-DD",
  "quantity": 8,
  "is_complete": true,
  "current_streak": 7,
  "longest_streak": 12,
  "streak_freeze_used": false
}
```

- Idempotent per (habit, date); re-submit with higher quantity → replace with max
- Streak updated atomically; triggers reminder suppression; emits analytics event

### HM-008 — Undo completion
**Priority:** M | **Sprint:** 3 | **Type:** Backend

```
DELETE /habits/{habit_id}/completions/{completion_id}
// Only today's completions (user TZ); older → 403
// Streak recalculated; reminder un-suppressed if time still ahead
```

### HM-009 — Batch sync (offline support)
**Priority:** H | **Sprint:** 3 | **Type:** Backend

```
POST /habits/completions/batch

Request: { "completions": [{ "habit_id", "completion_date", "quantity", "completed_at", "client_id", "source" }] }
Response: { "succeeded": [{ "client_id", "completion_id" }], "failed": [{ "client_id", "error_code", "message" }] }
// Partial success expected; each item processed independently
// Conflict resolution: latest completed_at wins
```

### HM-010 — Streak engine
**Priority:** H | **Sprint:** 3 | **Type:** Backend

- Walk back from today on each completion write; day = frequency rule met
- Streak freeze: 1 per ISO week, max 2 stored; auto-applied when streak ≥ 3 and scheduled day missed
- Vacation days excluded; freeze use logged in `streak_events` table

### HM-011 — Habit stacking
**Priority:** M | **Sprint:** 4 | **Type:** Full-stack

- `anchor_habit_id` groups habits in today view
- Anchor completion triggers nudge push: "Now: [anchored habit]"

### HM-012 — Vacation mode
**Priority:** M | **Sprint:** 4 | **Type:** Full-stack

```
POST /users/me/vacation  body: { "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }
DELETE /users/me/vacation/{id}
// End ≥ start; max 30 days; only one active/future vacation at a time
// Completions during vacation still count; streak engine excludes vacation days
```

---

## 4. AI Habit Generation

### AI-001 — Onboarding question flow
**Priority:** H | **Sprint:** 5 | **Type:** Full-stack

```
GET  /ai/onboarding/questions
// Returns next 3-5 questions; types: single_select|multi_select|scale|free_text

POST /ai/onboarding/answers
// Persists to user_ai_profile; progressive profiling over first 14 days
```

### AI-002 — Generate starter habits
**Priority:** H | **Sprint:** 5 | **Type:** Backend

```
POST /ai/habits/generate
Request: { "mode": "starter|expanded" }
Response: { "suggestions": [{ "suggestion_id", "title", "description", "category", "frequency_type", "quantity_target", "duration_minutes", "difficulty", "rationale" }] }
```

- Archetype hash lookup → cache hit (TTL 30d) or LLM call
- `starter`: 5–7 suggestions within 5s (cached) / 12s (cold)
- `expanded`: 30–40 suggestions
- LLM failure → fall back to curated default set
- Rate limit: 10 generations/user/day

### AI-003 — Accept/reject/modify suggestions
**Priority:** H | **Sprint:** 5 | **Type:** Backend

```
POST /ai/habits/accept
Request: { "suggestion_ids": ["uuid"], "modifications": { "uuid": { ...partial habit fields... } } }
Response: { "created_habits": [{ "habit_id": "uuid" }] }
// Calls HM-001 internally; logs acceptance for feedback loop
```

### AI-004 — Natural-language habit modification
**Priority:** M | **Sprint:** 5 | **Type:** Backend

```
POST /habits/{habit_id}/modify-nl
Request: { "instruction": "make it easier" }
Response: { "proposed_changes": { ...partial habit... }, "explanation": "string" }
// No change applied without explicit PATCH confirmation; returns within 8s
```

### AI-005 — Continuous coaching review
**Priority:** M | **Sprint:** 5 | **Type:** Backend

```
GET  /ai/coaching/reviews/latest
POST /ai/coaching/reviews/{review_id}/respond
     body: { "decisions": [{ "proposal_id", "action": "accept|modify|dismiss", "modification": {} }] }
// Proposal types: drop, scale_up, scale_down, restack, add_stack, add_new
// Default cadence: 7 days; configurable per user
```

### AI-006 — Safety guardrails
**Priority:** H | **Sprint:** 5 | **Type:** Backend

- Disallowed: medication advice, extreme calorie restriction, extreme exertion
- Targets above safe thresholds hedged with disclaimer or downgraded
- Pregnancy / disability / chronic illness flags suppress incompatible suggestions
- Test suite: 20 adversarial prompts

### AI-007 — LLM cost control & caching
**Priority:** H | **Sprint:** 5 | **Type:** Backend

- Target: ≥ 70% cache hit rate after 30 days
- Rate limit: 10 generations + 5 NL modifications/user/day
- Prompt templates versioned; A/B test framework supported

---

## 5. Reporting & Analytics

All report endpoints require Auth. Default range: 30d unless specified.

### RP-001 — Event ingestion pipeline
**Priority:** H | **Sprint:** 7

- Events: `habit_completed`, `habit_missed`, `streak_changed`, `mood_logged`, `program_day_completed`, etc.
- Async queue; producer never blocks user-facing write
- Backfill job for historical data

### RP-002 — Pre-aggregation jobs
**Priority:** H | **Sprint:** 7

- Daily rollup: completion count/habit, total minutes, mood average
- Weekly/monthly derived from daily; idempotent

### RP-003 — Completion rate
```
GET /reports/completion-rate?range=7d|30d|90d|year|all|custom&from=&to=&habit_id=
Response: { "range", "overall_completion_rate", "per_habit": [{ "habit_id", "title", "completion_rate", "completions", "expected" }] }
// ≤ 2s for 24 months; custom range up to 24 months
```

### RP-004 — Missed-habit trends
```
GET /reports/missed-trends?range=
Response: [{ "date", "missed_count", "total_scheduled" }] + "trend_direction": "improving|stable|declining"
```

### RP-005 — Weekly performance
```
GET /reports/weekly?week=YYYY-Www
Response: day-by-day breakdown, top habits, missed habits, WoW delta, AI narrative summary
```

### RP-006 — Monthly performance
```
GET /reports/monthly?month=YYYY-MM
```

### RP-007 — Consistency score
```
GET /reports/consistency-score
// 0-100, weighted by habit difficulty + streak length, rolling 30 days
```

### RP-008 — 365-day heatmap
```
GET /reports/heatmap?habit_id=&end_date=
Response: [{ "date": "YYYY-MM-DD", "completion_rate": 0.0-1.0, "intensity_bucket": 0-4 }]  // 365 items
```

### RP-009 — Streak dashboard
```
GET /reports/streaks
Response: per-habit { "current_streak", "longest_streak", "at_risk": bool, "risk_reason": "string" }
// At-risk: today is typically-missed day AND not completed AND > X% historical miss rate on weekday
```

### RP-010 — Time-of-day heatmap
```
GET /reports/time-of-day?habit_id=
Response: 24h × 7-day grid of completion counts
```

### RP-011 — Day-of-week breakdown
```
GET /reports/day-of-week
Response: per-weekday completion rate across all active habits + per-habit breakdown
```

### RP-012 — Habit correlation matrix
```
GET /reports/correlations
Response: matrix of habit pairs with co-occurrence probability P(B|A)
// Requires ≥ 14 days of history per pair
```

### RP-013 — Momentum index
```
GET /reports/momentum
Response: { "score_7d": 72, "score_30d": 68, "score_90d": 65, "trend": "improving" }
```

### RP-014 — Failure pattern analysis
```
GET /reports/failure-patterns?habit_id=
Response: clusters of misses by day-of-week, time, calendar density + human-readable insight strings
```

### RP-015 — Mood × habit correlation
```
GET /reports/mood-correlation
// Requires ≥ 14 days of mood data; else 422 INSUFFICIENT_DATA
Response: per-habit mood_delta (avg mood: completed vs. uncompleted days) + significance indicator
```

### RP-016 — Sleep × habit correlation
```
GET /reports/sleep-correlation  // Same shape as RP-015; uses HealthKit/Fit sleep data
```

### RP-017 — Identity progress
```
GET /reports/identity?tag=runner
Response: days behaving consistent with identity (any tagged habit completed that day)
```

### RP-018 — Time investment
```
GET /reports/time-investment?range=
Response: total minutes by category, by habit, month-over-month delta
```

### RP-019 — Bad-habit savings counter
```
GET /reports/savings?program_enrollment_id=
Response: { "money_saved", "currency", "calories_avoided", "hours_reclaimed", "days_clean" }
```

### RP-020 — Habit health timeline
```
GET /programs/{program_id}/health-timeline?days_clean=N
Response: achieved, current, upcoming milestones with descriptions and source citations
```

### RP-021 — Weekly review (auto-narrative)
```
// Scheduled job: Sunday 18:00 user-local time
GET /reports/weekly-review/latest
Response: { "period": "2026-W18", "narrative": "string (≤200 words)", "highlights": [...], "concerns": [...], "next_week_suggestions": [...] }
```

### RP-022 — Report export
```
POST /reports/{report_id}/export?format=png|csv
// Returns signed URL; image rendered server-side
```

---

## 6. Notifications & Reminders

### NT-001 — Notification scheduling service
**Priority:** H | **Sprint:** 9

- Dispatch via APNs + FCM; within 60s of scheduled time
- Suppression rules evaluated at dispatch time (not scheduling time)

### NT-002 — Reminder CRUD
```
PUT /habits/{habit_id}/reminders  body: { "reminder_times": ["07:30", "20:00"] }
// Max 3 per habit; replaces existing atomically
```

### NT-003 — Smart suppression: completed habit
- Skip reminder if habit already completed today (manual or auto_health)

### NT-004 — Smart suppression: quiet hours & DND
- Honor `notification_quiet_hours` from profile
- Notifications in quiet window deferred to window end (or skipped if window > 6h)

### NT-005 — Smart suppression: calendar busy
- Google Calendar busy block → skip reminder; show as in-app card instead

### NT-006 — Reminder time learning
- If median completion time differs from reminder time by > 1h for 14+ days → propose shift
- Never auto-applies; proposal requires user consent toggle

### NT-007 — Streak-risk & comeback notifications
- Streak-risk: 2h before midnight if streak ≥ 7 and habit incomplete on scheduled day
- Comeback: warm message after 2+ missed days (not shame-based)

### NT-008 — Weekly review notification
- Sunday evening; user-local time; configurable

### NT-009 — Notification preferences API
```
GET /users/me/notification-preferences
PUT /users/me/notification-preferences
// Categories: habit_reminders, streak_risk, comeback, weekly_review, program_daily, marketing
// Each individually toggleable
```

---

## 7. Motivation / Bad-Habit Removal

### BH-001 — Program library data model
**Priority:** H | **Sprint:** 10

```sql
-- programs: program_id, slug, title, description, bad_habit_type, default_length_days, is_clinical_risk
-- program_days: program_day_id, program_id, day_number, audio_url, task_text, reflection_prompt
```
- At least 2 programs at launch (alcohol, smoking); reviewed by behavioral-science consultant

### BH-002 — Program enrollment
```
POST /programs/{program_id}/enroll

Request:
{
  "start_date": "YYYY-MM-DD",
  "replacement_habit_ids": ["uuid"],   // at least 1 required
  "triggers": [...],                   // at least 3: { "category": "emotion|location|time|person|situation", "value": "string" }
  "personal_reasons": ["string"],      // at least 1
  "accountability_contact": { "name", "phone_or_email" }
}

Response: { "enrollment_id": "uuid", "current_day": 1, "next_day_unlocks_at": "iso" }
// Day 1 unlocked immediately; subsequent days unlock at user's local midnight
// is_clinical_risk → show disclaimer before enrollment
```

### BH-003 — Daily program content
```
GET /programs/enrollments/{enrollment_id}/today
Response: { "day_number", "audio_url" (signed), "audio_duration_seconds", "task_text", "reflection_prompt",
            "savings_to_date": { "money", "currency", "calories_avoided", "hours_reclaimed" },
            "days_since_last_slip", "is_completed" }
```

### BH-004 — Mark program day complete
```
POST /programs/enrollments/{enrollment_id}/days/{day_number}/complete
Request: { "audio_listened": true, "task_done": true, "reflection_text": "string?" }
```

### BH-005 — Log relapse / slip
```
POST /programs/enrollments/{enrollment_id}/slip
Request: { "slip_date": "YYYY-MM-DD", "trigger_id": "uuid?", "notes": "string?" }
// Resets days_since_last_slip to 0; does NOT zero cumulative total_clean_days
// Returns supportive message + next steps
```

### BH-006 — Urge SOS flow
```
GET /programs/enrollments/{enrollment_id}/urge-sos
Response: { "urge_audio_url", "breathing_pattern": { "inhale_seconds": 4, "hold_seconds": 7, "exhale_seconds": 8, "cycles": 4 },
            "personal_reasons": [...], "accountability_contact": { "name", "channel": "sms|email", "deeplink" } }
// Reachable in ≤ 2 taps; works offline (audio cached)
```

### BH-007 — Trigger logging
```
POST /programs/enrollments/{enrollment_id}/triggers
GET  /programs/enrollments/{enrollment_id}/triggers
```

### BH-008 — Personal motivational uploads
```
POST /uploads  (multipart)
// Audio: ≤10 MB, formats: mp3|m4a|wav
// Images: ≤5 MB, formats: jpg|png|webp
// Quota: max 50 uploads per user
// Antivirus scan required; user-private only
GET /uploads
DELETE /uploads/{upload_id}
```

### BH-010 — Clinical disclaimer & crisis resources
- Required for `is_clinical_risk=true` programs
- User must acknowledge before enrollment
- Crisis helpline link visible on every program screen (region-aware)

### BH-011 — Anonymous community check-ins
```
POST /community/check-ins       // ≤280 chars; profanity filtered; 3/day rate limit
GET  /community/feed?program_id=
// Opt-in; anonymous handle (e.g., "Member-A1B2"); admin moderation queue
```

---

## 8. Daily Insight

### DI-001 — Content data model
```sql
-- daily_insights: insight_id, title, category, image_banner_url, audio_url, audio_duration_seconds,
--                 script_text, published_at, tags[], add_as_habit_template_id (nullable)
```
- Categories: Money, Relationships, Career, Health, Mindset, Communication, Parenting, Focus

### DI-002 — Personalized feed
```
GET /daily-insights/feed?cursor=&limit=20
Response: { "items": [{ "insight_id", "title", "category", "image_banner_url", "audio_duration_seconds", "is_saved", "is_favorited" }], "next_cursor" }
// Ranked by user interests + habit data signals; ≤ 20/page; < 1.5s
```

### DI-003 — Insight detail + audio
```
GET /daily-insights/{insight_id}
// Returns full detail including signed audio URL and add_as_habit payload
// Background audio; lock-screen controls; resume from last position; analytics on play/complete
```

### DI-004 — Save / favorite / note
```
POST   /daily-insights/{insight_id}/save
DELETE /daily-insights/{insight_id}/save
POST   /daily-insights/{insight_id}/favorite
DELETE /daily-insights/{insight_id}/favorite
PUT    /daily-insights/{insight_id}/note  body: { "note": "string" }
```

### DI-005 — "Add as habit" CTA
- Tap → pre-fill habit-creation form with template values; user edits before saving

### DI-006 — Offline download (premium)
```
POST /daily-insights/{insight_id}/download  → signed URL valid 30 days (premium-gated)
```

---

## 9. Reflection & Journaling

### RJ-001 — Mood log
```
POST /mood-logs  body: { "log_date": "YYYY-MM-DD", "score": 1-5, "note": "string?" }
GET  /mood-logs?from=&to=
// One log per date (upsert); encrypted at rest
```

### RJ-002 — Journal entry CRUD
```
POST  /journal-entries  body: { "entry_date": "YYYY-MM-DD", "text": "string (≤5000)", "habit_ids": ["uuid"] }  // max 5 habit tags
GET   /journal-entries?from=&to=&habit_id=
PATCH /journal-entries/{id}
DELETE /journal-entries/{id}  // soft delete
// Encrypted at rest
```

### RJ-004 — Evening reflection prompt
- Daily local notification at user-configurable time
- Deep links to combined mood + journal screen
- Respects DND/quiet hours

---

## 10. Integrations

### IN-001 — Apple HealthKit
- Read: steps, sleep, workouts, mindful minutes, water, weight
- `HKObserverQuery` background delivery
- Auto-complete via HM-007 with `source=auto_health`
- User disables per-category in settings

### IN-002 — Google Fit
- Equivalent to IN-001 via Google Fit REST + Fitness API

### IN-003 — Calendar integration
```
POST /integrations/calendar/connect   // OAuth flow start
DELETE /integrations/calendar
// Read-only free/busy; never reads event details without explicit consent
```

### IN-004 — Integration management
```
GET /users/me/integrations
Response: per-integration { "connected", "last_synced_at", "enabled_categories[]" }
```

---

## 11. Wearables & Widgets

### WW-001 — iOS home-screen widget
- WidgetKit; small/medium/large variants; complete via App Intent; updates within 5 min

### WW-002 — Android home-screen widget
- Glance API; equivalent functionality and update cadence

### WW-003 — Apple Watch app
- Independent (cached data); complications: streak count, today's progress; haptics on completion

### WW-004 — Wear OS app
- Tile + standalone UI; parity with watchOS

### WW-005 — iOS Shortcuts & Android Quick Tiles
- App Intents (iOS) + Quick Settings tiles (Android) for one-tap habit completion

---

## 12. Subscription & Billing

### SUB-001 — Tiers & entitlements
```sql
-- subscriptions: user_id, tier (free|premium), provider (apple|google), provider_subscription_id, status, expires_at, auto_renew
```

| Tier | Habits | Reports | Programs | Daily Insight | AI Coach |
|---|---|---|---|---|---|
| Free | Limited (N) | Core | — | Free tier | — |
| Premium | Unlimited | All | All | Full library | ✓ |

### SUB-002 — Apple IAP (StoreKit 2)
- Server-side receipt verification; webhook for renewals/cancellations

### SUB-003 — Google Play Billing
- Play Billing Library + RTDN webhook

### SUB-004 — Paywall enforcement
- Middleware: premium-gated endpoints return 402/403 `UPGRADE_REQUIRED` for free users

---

## 13. Admin / Content Curator

### ADM-001 — Admin auth & RBAC
- Roles: `admin`, `content_curator`
- All admin actions audit-logged

### ADM-002 — Daily Insight CMS
- CRUD + versioning for Daily Insight content; scheduled publish; audio/image upload

### ADM-003 — Bad-habit program CMS
- Day-level editor; reorder days; version + rollback; clinical-risk flag per program

### ADM-004 — User upload moderation queue
- Review queue for community check-ins and reported uploads
- Approve/reject/ban; bulk operations; SLA dashboard

### ADM-005 — Aggregated analytics dashboard
- Internal metrics: DAU, MAU, retention, conversion, AI cache hit rate
- No PII exposed

---

## Cross-Cutting QA

| Task | Priority | Sprint |
|---|---|---|
| QA-001 End-to-end test suite | H | Continuous |
| QA-002 Performance test (1k concurrent users, 24-month queries, 500-item batch sync) | H | 16 |
| QA-003 Security audit & pen test (annual third-party) | H | 16 |
| QA-004 Accessibility audit (WCAG 2.1 AA, VoiceOver, TalkBack) | H | 16 |
| QA-005 Localization readiness (strings externalized, pseudo-L10n, date/time/currency) | L | 16 |

---

## Non-Functional Requirements Summary

### Performance
- Home screen: < 1s on 4G, 4-year-old device
- Habit complete UI response: < 100ms
- Reports: < 2s for 24 months of history
- AI suggestions: < 5s cached / < 12s cold
- Cold-start: < 2.5s

### Security
- TLS 1.2+ in transit; AES-256 at rest
- OAuth 2.0 / OIDC; rotating refresh tokens
- Health data never shared with third parties for advertising
- Annual third-party pen test before public release
- All user uploads virus-scanned + content-type validated

### Availability
- Backend: ≥ 99.9% monthly
- Offline mode: habit completion, journaling, viewing cached data
- Daily backups retained 30 days

### Compliance
- GDPR: access, rectification, erasure, portability
- Apple App Store + Google Play policies
- Clinical disclaimers for substance-cessation programs
- Privacy policy + ToS visible before account creation

---

## Database Schema — Key Tables

```sql
-- Audit columns on every table
created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
deleted_at    TIMESTAMPTZ  -- soft delete

-- Core indexes
CREATE INDEX ON habit_completions (user_id, completion_date);
CREATE INDEX ON journal_entries (user_id, entry_date);
```

---

## API Conventions

- All endpoints prefixed: `/api/v1`
- Authentication: `Authorization: Bearer <access_token>`
- Timestamps: ISO 8601 UTC
- Pagination: cursor-based (`cursor` + `next_cursor`)
- Partial updates: `PATCH` with only changed fields
- Errors follow format: `{ "error_code": "SNAKE_CASE", "message": "string", "details": {} }`
- Versioning: all endpoints versioned (NFR-MN-005)

### Common Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `EMAIL_TAKEN` | 409 | Duplicate email on signup |
| `DISPOSABLE_EMAIL` | 422 | Blocked disposable email domain |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `ACCOUNT_DEACTIVATED` | 403 | Soft-deleted account |
| `REFRESH_EXPIRED` | 401 | Refresh token past TTL |
| `INVALID_TOKEN` | 401 | Token validation failed |
| `TIER_LIMIT_REACHED` | 403 | Free tier habit limit |
| `INSUFFICIENT_DATA` | 422 | Not enough data for report |
| `UPGRADE_REQUIRED` | 402 | Premium-gated feature |
| `HABIT_NOT_FOUND` | 404 | Habit deleted or not owned |

---

## Dependency Graph

```
INFRA-001/002/003/004/005
        │
        ▼
   AUTH-001..013
        │
        ├──► HM-001..015 ──► RP-001..023
        │                       │
        │                       ├──► RP-021 needs AI-002
        │                       └──► RP-019/020 need BH-*
        │
        ├──► AI-001..007 (depends on AUTH + HM)
        │
        ├──► IN-001..005 ──► HM-007 (auto-completion)
        │
        ├──► NT-001..010 (depends on HM + IN-003)
        │
        ├──► BH-001..013 (depends on HM + INFRA + ADM)
        │
        ├──► DI-001..007 (depends on ADM + INFRA)
        │
        ├──► RJ-001..005 (depends on AUTH + NT)
        │
        ├──► WW-001..005 (depends on HM + Mobile UIs)
        │
        ├──► SUB-001..005 (depends on AUTH; gates premium)
        │
        └──► ADM-001..005 (parallel; gates content delivery)
```

---

*Total Tasks: ~95 across 13 modules | SRS v1.0 | May 2026*
