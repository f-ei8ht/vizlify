# ADR-0003: TanStack Query as the only server-state layer

- **Status:** accepted
- **Date:** 2026-10-19
- **Deciders:** frontend

## Context

The dashboard will show lists, details and mutations for six domains, plus
approval actions that must feel instant. The data is owned by the server; the
browser only mirrors it.

Common failure modes in this situation:

- copying server data into `useState` and letting it drift;
- a global store that reimplements caching, retries and invalidation;
- hand-written loading and error handling in every screen.

The frontend also needs optimistic updates for edits and deletes, and it must
avoid retrying errors that will never succeed (401, 422, 404).

## Decision

Use **TanStack Query** for every read and write that touches the API.

- Query keys are hierarchical per domain (`["projects", id, "milestones"]`).
- `queryOptions` and hooks live beside each other in `lib/api/<domain>.ts`.
- Mutations own optimistic updates, rollback and targeted invalidation.
- UI state stays in React state; Query never stores form drafts or dialogs.
- One `QueryClient` per browser tab, a fresh one per server render.

## Consequences

**Easier**

- One cache, one retry policy, one place to inspect data (Devtools).
- Optimistic edits with a correct rollback path.
- Screens use `DataState` for loading, error and empty states.
- Invalidation is precise: a milestone change does not refetch clients.

**Harder**

- Query keys must be designed; a wrong key causes stale screens.
- Optimistic updates add code that must be tested once UI tests exist.
- Server Components cannot use client hooks; server-rendered screens will need
  a hydration or prefetch strategy later.
- Devtools add a development-only dependency.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| SWR | Smaller, but weaker mutation and optimistic-update ergonomics |
| Redux Toolkit Query | Requires a global store and more ceremony for a small app |
| Zustand + manual fetch | Reimplements caching, dedupe, retries and invalidation |
| Server Components only | The approval queue and optimistic actions need client interactivity |

## Revisit if

- Most screens become server-rendered and prefetching dominates.
- Real-time updates (webhooks pushed to the browser) require a socket layer;
  Query can still own the cache, but the transport changes.
- Bundle size becomes a measured problem on the hosted demo.
