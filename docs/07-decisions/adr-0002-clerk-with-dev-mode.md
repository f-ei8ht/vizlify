# ADR-0002: Clerk with a fail-closed local `dev` mode

- **Status:** accepted
- **Date:** 2026-10-18
- **Deciders:** backend, frontend

## Context

Two audiences need to run Vizlify:

1. **Judges and new contributors**, who should reach a working app in minutes
   without creating accounts or handling keys.
2. **The hosted demo**, which needs real sign-in, session management and
   account isolation.

Building auth from scratch means password hashing, reset flows, session
storage and a long list of ways to get it wrong. The hackathon timeline does
not allow that, and auth is not the differentiator.

## Decision

Use **Clerk** for hosted authentication and a `dev` mode for local runs:

- The frontend wraps the app in `ClerkProvider` and attaches a session token to
  every API call.
- The backend verifies the token locally with `clerk-backend-api` and the
  public key, then maps the subject to a local `users` row.
- `AUTH_MODE=dev` resolves a seeded user by email and is **refused** when
  `APP_ENV=production`.
- The frontend does not branch on mode; the backend decides.

## Consequences

**Easier**

- No password storage, reset flow or session table to secure.
- Judges run the app with zero keys.
- Identity is a dependency (`CurrentUser`) everywhere, so ownership checks are
  uniform.
- Clerk handles MFA and account UI later without backend changes.

**Harder**

- The hosted demo depends on an external identity service.
- Provisioning has two mapping paths (Clerk id, then email), which must stay
  deterministic.
- Dev mode is dangerous if exposed; the production guard is load-bearing and
  tested.
- Self-hosting without Clerk requires a new auth implementation.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Custom email + password | Too much security surface for the timeline |
| Auth0 | Heavier setup; Clerk's Next.js SDK is faster here |
| Supabase Auth | Would pull in a second database/auth model |
| No auth in the demo | Cannot demonstrate ownership or a real approval queue |

## Revisit if

- The project needs organizations/teams with Clerk-level granularity beyond the
  current single-workspace model.
- Hosting constraints make Clerk unaffordable or unavailable.
- A self-hosted requirement appears; the `CurrentUser` boundary would remain,
  only verification changes.
