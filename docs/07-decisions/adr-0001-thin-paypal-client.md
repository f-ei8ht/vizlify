# ADR-0001: A thin async PayPal client over a generated SDK

- **Status:** accepted
- **Date:** 2026-10-20
- **Deciders:** backend

## Context

Vizlify needs Invoicing v2, Payouts v1 and webhook verification. The two
obvious options are PayPal's generated server SDK and a hand-written HTTP layer.

Constraints:

- FastAPI is async end to end; blocking calls would need thread offloading.
- Tests must run without PayPal credentials or network access.
- The hackathon asks for APIMatic's PayPal Context Plugin to be used as a
  reference, and the roadmap suggests the official SDK where it covers an API.
- Idempotency and retry semantics are security-relevant and must be explicit.
- Every PayPal call needs a mock path so judges can run the app with no keys.

The official Python server SDK is synchronous, generated, and difficult to
intercept at the transport. Mocking it means patching generated classes.

## Decision

Write a small async client in `backend/app/paypal/` on top of `httpx`:

- one OAuth token cache with single-flight refresh;
- one retry policy matching PayPal's documented rules;
- explicit `PayPal-Request-Id` generation;
- a transport-level mock (`httpx.MockTransport`) rather than a fake service.

Use APIMatic's context plugin as a documentation source and record evidence,
not as a code generator.

## Consequences

**Easier**

- Async without thread pools.
- Tests inject `MockTransport`, a fake clock and a sleep recorder; the suite
  runs in milliseconds.
- Retry and idempotency behavior is visible, reviewable and covered by tests.
- One place to add logging, metrics and error translation.
- The mock exercises the real client code paths, so switching to sandbox is one
  environment variable.

**Harder**

- We own endpoint payload shapes and must track PayPal API changes.
- Less sponsor-alignment than shipping generated SDK code.
- New endpoints need both a method and a mock route.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| `paypal-server-sdk` (sync) | Blocks the event loop or needs `run_in_threadpool` around every call; hard to mock |
| APIMatic-generated SDK | Same sync and mocking issues; generated code obscures retry policy |
| Raw `httpx` calls in services | Duplicates token and retry logic; impossible to enforce idempotency centrally |
| `requests` + threading | Wrong runtime model for FastAPI |

## Revisit if

- PayPal publishes an async first-party SDK with a mockable transport.
- The surface grows beyond a few endpoints and generated types would save more
  than they cost.
- APIMatic's plugin can generate an async client that passes the same tests.
