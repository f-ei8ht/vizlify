# Part 7 — Decisions

> [Handbook index](../README.md) · **Part 7 of 9**

Architecture Decision Records (ADRs) explain **why** a choice was made, what was
rejected, and what would make us revisit it. They are short by design.

## Index

| ADR | Decision | Status |
|-----|----------|--------|
| [0001](./adr-0001-thin-paypal-client.md) | A thin async PayPal client over a generated SDK | Accepted |
| [0002](./adr-0002-clerk-with-dev-mode.md) | Clerk with a fail-closed local `dev` mode | Accepted |
| [0003](./adr-0003-tanstack-query.md) | TanStack Query as the only server-state layer | Accepted |

## Template

```md
# ADR-NNNN: Title

- Status: proposed | accepted | superseded
- Date: YYYY-MM-DD
- Deciders: names or roles

## Context
What forces are at play?

## Decision
What we will do.

## Consequences
What becomes easier, what becomes harder.

## Alternatives considered
What we rejected and why.
```

## When to write one

Write an ADR when a choice:

- is expensive to reverse (database, auth provider, money flow);
- affects more than one layer (API and UI, code and deployment);
- will be questioned by a future contributor or judge.

Do not write one for naming a variable. The handbook is not a diary.

Next: [ADR-0001](./adr-0001-thin-paypal-client.md) →
