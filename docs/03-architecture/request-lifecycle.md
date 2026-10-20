# Request lifecycle

> [Handbook index](../README.md) · [Part 3](./README.md) · **Status: Implemented**

One authenticated API call, from click to JSON. The example lists clients.

## Happy path

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant N as Next.js
    participant C as Clerk
    participant F as FastAPI
    participant A as auth/deps.py
    participant S as services/clients.py
    participant D as PostgreSQL

    B->>N: Navigate to a screen
    N->>C: Read session cookie
    C-->>N: Signed-in user
    N-->>B: Shell + client bundle
    B->>C: getToken()
    C-->>B: Short-lived session token
    B->>F: GET /clients with Bearer token
    F->>A: Resolve CurrentUser
    A->>C: Verify JWT with public key, no network call
    C-->>A: Claims: sub, email
    A->>D: Find user by clerk_user_id, else by email, else create
    D-->>A: users row
    A-->>F: User
    F->>S: list_clients(session, owner_id)
    S->>D: SELECT … WHERE owner_id = :id
    D-->>S: Rows
    S-->>F: Model instances
    F-->>B: 200 {"data":[…],"error":null}
    B->>B: TanStack Query stores the result
```

### What each step guarantees

| Step | Guarantee |
|------|-----------|
| Clerk session | Identity is never trusted from the browser alone |
| Local JWT verification | No per-request call to Clerk; the public key is enough |
| Owner-scoped query | A user cannot read another user's rows, even with a guessed UUID |
| Envelope | The client never branches on raw JSON shape |
| Query cache | A second screen reuses fresh data for 30 seconds |

## Failure path

```mermaid
flowchart TD
    Call["API call"] --> Auth{"Signed in?"}
    Auth -- "No" --> E401["401 unauthorized<br/>code: unauthorized"]
    Auth -- "Yes" --> Valid{"Payload valid?"}
    Valid -- "No" --> E422["422 validation_error<br/>details: field, message, type"]
    Valid -- "Yes" --> Own{"Owned by user?"}
    Own -- "No" --> E404["404 not_found<br/>no existence leak"]
    Own -- "Yes" --> Work{"Business rule?"}
    Work -- "Violated" --> E409["409 conflict<br/>for example shares over 100%"]
    Work -- "OK" --> OK["200 / 201<br/>data set"]
    E401 --> Envelope["{ data: null, error: { code, message, details } }"]
    E422 --> Envelope
    E404 --> Envelope
    E409 --> Envelope
    OK --> Data["{ data: …, error: null }"]
```

Every failure uses the same envelope and the HTTP status carries the truth.
The frontend turns `error` into a typed `ApiError` once, in
`frontend/lib/api/client.ts`.

## Why ownership returns 404, not 403

A guessed UUID returns `404 not_found` rather than `403 forbidden`. Returning
403 would confirm that the row exists, which leaks information across
workspaces. `403` is reserved for a real permission problem on a resource the
caller can already see (planned roles).

## Where the agent will plug in

The agent will call the **same services**, not the routers, and its write paths
will end in a `PendingAction` instead of a PayPal call:

```mermaid
sequenceDiagram
    participant Agent as Agent tool
    participant S as Service
    participant P as PendingAction
    participant H as Human
    participant E as Executor
    participant PP as PayPal

    Agent->>S: propose_invoice(milestone)
    S->>P: insert status=pending, dedupe_key
    H->>P: approve
    H->>E: execute(action_id)
    E->>PP: create + send invoice
    PP-->>E: invoice id
    E->>P: status=executed, result
```

The agent never receives the executor dependency. That is enforced by
construction, not by prompt instructions.

Next: [Data model](./data-model.md) →
