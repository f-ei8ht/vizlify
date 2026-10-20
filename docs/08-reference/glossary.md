# Glossary

> [Handbook index](../README.md) · [Part 8](./README.md) · **Status: living document**

These terms have one meaning in Vizlify. Use them exactly in code, docs and UI.

## Money and workflow

| Term | Meaning |
|------|---------|
| **Proposal** | A `PendingAction` row describing something the agent wants to do. It has a kind, a validated payload, a rationale and a dedupe key. It does nothing on its own. |
| **Approval** | A human decision on a proposal. Approving authorises the executor; rejecting records a reason and closes it. |
| **Executor** | The only code path allowed to call PayPal for a money action. It runs only from an approved proposal. *(Planned.)* |
| **Action kind** | The type of a proposal: create/send/cancel invoice, send reminder, prepare/execute payout, draft dispute response. |
| **Dedupe key** | A unique string on a proposal. Re-running the same logical action cannot create a second proposal. |
| **Audit log** | Append-only record of proposals, approvals, rejections and executions. Deleting a user keeps the log with a null user. |
| **Spend cap** | A configured maximum for a payout or a day. The executor blocks anything above it. *(Planned.)* |
| **Kill switch** | A setting that stops all agent actions immediately. *(Planned.)* |
| **Step-up confirmation** | Re-authentication before a payout above a threshold. *(Planned.)* |

## Billing

| Term | Meaning |
|------|---------|
| **Client** | The agency's customer. Has an email and a preferred reminder tone. |
| **Project** | A piece of work for one client, in one currency. |
| **Milestone** | A billable unit of a project with an amount and a due date. Status: `todo`, `done`, `billed`. |
| **Invoice** | A PayPal invoice mirroring a milestone. Status: `draft`, `sent`, `paid`, `partially_paid`, `cancelled`, `refunded`. |
| **Nudge / reminder** | A tone-aware message sent through PayPal for an overdue invoice. |
| **Overdue** | An invoice past its due date with a status other than paid or cancelled. |
| **Payout** | A PayPal batch that sends the team their share of a paid invoice. |
| **Payout item** | One freelancer's line inside a payout batch. |
| **Split** | The percentage allocation across team members. Must never exceed 100%. |
| **Largest remainder** | The deterministic rounding method planned for splits, so items sum exactly to the invoice total. |
| **Reconciliation** | Comparing local invoice and payout state against PayPal and reporting drift. *(Planned.)* |

## Agent

| Term | Meaning |
|------|---------|
| **Brief** | Pasted client text used to draft scope, milestones and prices. Untrusted input. |
| **Scope** | The proposed project structure returned by the agent: milestones, amounts, assumptions. |
| **Mock mode** | `LLM_MODE=mock` or `PAYPAL_MODE=mock`. Deterministic, no keys, no network. |
| **Tool** | A function the agent may call. Read tools answer questions; propose tools create proposals; there is no execute tool. |
| **Prompt injection** | Untrusted text trying to make the agent act outside its rules. Treated as data, never instructions. |
| **Eval** | A committed test case for agent output quality. *(Planned.)* |

## Platform

| Term | Meaning |
|------|---------|
| **Workspace / agency** | The owner's data boundary. Every row is scoped to one user today; roles are planned. |
| **Owner** | The authenticated user who owns clients, projects and proposals. |
| **Envelope** | The `{ data, error }` shape of every API response. |
| **Mode** | A startup configuration choice: `AUTH_MODE`, `PAYPAL_MODE`, `LLM_MODE`, `JOBS_MODE`. |
| **Sandbox** | PayPal's test environment. The hackathon build only uses this. |
| **Live** | Real money. The mode exists in code but is refused outside production. |
| **Migration** | A versioned Alembic change to the database schema. |
| **Seed** | The idempotent command that creates the fictional Northwind Studio agency. |

## Naming rules

| Prefer | Avoid |
|--------|-------|
| `proposal` | `task`, `job`, `request` |
| `payout` | `payment`, `transfer` |
| `invoice` | `bill` |
| `milestone` | `phase`, `stage` |
| `client` | `customer`, `account` |
| `agency` | `workspace`, `tenant` (unless discussing multi-tenancy) |

Consistency matters because these words appear in database columns, API
payloads and the UI. A synonym in one layer becomes a bug in another.

Next: [Status and roadmap](../09-project/status-and-roadmap.md) →
