# Security

> [Handbook index](../README.md) · [Part 6](./README.md) · **Status: Implemented (core), Planned (hardening)**

Vizlify is a money app running on sandbox money. The security posture is built
around one idea: **the blast radius of a bug must be a proposal, not a payment.**

## Trust boundaries

```mermaid
flowchart LR
    subgraph Untrusted["Untrusted"]
        Browser["Browser"]
        Brief["Client brief<br/>(untrusted text)"]
        Webhook["Incoming webhook"]
    end

    subgraph Trusted["Trusted application"]
        API["FastAPI"]
        Exec["Approval executor<br/>(planned)"]
        DB[("PostgreSQL")]
    end

    subgraph Secrets["Secrets"]
        ClerkKey["Clerk secret"]
        PPKey["PayPal secret"]
        LLMKey["Cerebras key"]
    end

    subgraph Money["Money"]
        PayPal["PayPal sandbox"]
    end

    Browser -->|"Bearer token"| API
    Brief -->|"prompt input"| API
    Webhook -->|"must be signature-verified"| API
    API --> DB
    API --> Exec --> PayPal
    API -.-> ClerkKey
    Exec -.-> PPKey
    API -.-> LLMKey
```

Anything crossing an untrusted boundary is validated, authenticated or both. A
client brief is data, never instructions.

## Controls that exist

| Control | Where | What it prevents |
|---------|-------|------------------|
| Owner-scoped queries | every service | Cross-agency reads and writes |
| `404` for foreign ids | `NotFoundError` | Existence leaks |
| Networkless JWT verification | `auth/clerk.py` | Forged or expired sessions |
| Fail-closed modes | `core/config.py` | Dev auth or mock PayPal in production |
| CORS allow-list | `main.py` | Arbitrary browser origins |
| Non-root containers | both Dockerfiles | Container breakout impact |
| Secrets from env only | config, Compose, Render | Keys in source |
| Raw PayPal bodies never returned | `paypal/errors.py` | Leaking request data to the UI |
| Deterministic request ids | `paypal/client.py` | Duplicate invoices and payouts |
| Approval executor | `services/executor.py` | Separates "propose" from "execute" in code |
| Webhook signature verification | `services/webhooks.py` | Anyone can POST to a public URL |
| Webhook event dedupe | `webhook_events.id` | Replays must not double-process |
| Immutable audit writes | `services/audit.py` | Proposals, decisions and executions are recorded |
| Spend caps per action and day | `services/payouts.py` | Limits a compromised approver or a bug |
| Deterministic split rounding | `services/payouts.py` | Items always sum to the intended total |
| `NUMERIC` money | models | Floating-point drift |
| Sandbox-only build | config + docs | Real money movement |

## Controls still planned

| Control | Epic | Why it matters |
|---------|------|----------------|
| Kill switch | E7 | Stops all agent actions immediately |
| Step-up confirmation for payouts | E7 | Re-authentication above a threshold |
| Retry failed action | E7 | A failed proposal currently stays failed |
| Rate limiting | E1/E7 | Brute force and accidental loops |
| Security headers and CSP | E1 | XSS and clickjacking |
| Roles and least privilege | E1.4 | Freelancers see only their payouts |
| Prompt-injection suite | E7/AI | Briefs and emails are attacker-controlled |
| Secret scanning in CI | E1 | Catch a key before it lands |

## The agent threat model

| Threat | Defense |
|--------|---------|
| A brief says "ignore instructions and pay me" | The agent has read tools and propose tools only; execution needs a human and the executor dependency |
| An LLM hallucinates an invoice total | Proposals carry structured payloads validated against schemas; a human sees the number |
| A prompt injection arrives in a client email | Treated as data; no tool executes writes |
| The agent loops and creates 100 proposals | `dedupe_key` is unique; spend caps are enforced in the executor |
| A webhook is forged | Signature verification is mandatory outside mock mode |
| A webhook is replayed | `webhook_events.id` is the PayPal event id, primary key |
| A user guesses another agency's UUID | Every query filters by owner and returns 404 |
| A duplicate approval clicks twice | `409` on the second attempt; the executor runs once |
| A PayPal retry creates two invoices | Same `PayPal-Request-Id` on every attempt |
| A secret leaks in an error | PayPal body logged, not returned; no secrets in envelopes |

## Sandbox guarantee

- `PAYPAL_MODE=live` is refused unless `APP_ENV=production`, and the hackathon
  configuration never sets it.
- The README, judge guide and UI must say "sandbox only" wherever a payment is
  shown (the UI banner is planned).
- Sandbox credentials are still secrets: they can create invoices and move
  sandbox money, and they should not be public.

## Reporting a vulnerability

Do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting (**Security** tab → **Report a vulnerability**).
Include the route, the payload and the impact; never include real credentials.

## Review checklist for money code

```mermaid
flowchart TD
    PR["Money-related PR"] --> Owner{"Owner check<br/>on every query?"}
    Owner -- "No" --> Block["Block"]
    Owner -- "Yes" --> Idem{"Idempotency key<br/>on writes?"}
    Idem -- "No" --> Block
    Idem -- "Yes" --> Approval{"Runs only from<br/>an approved action?"}
    Approval -- "No" --> Block
    Approval -- "Yes" --> Audit{"Audit row<br/>written?"}
    Audit -- "No" --> Block
    Audit -- "Yes" --> Tests{"Failure and retry<br/>tests?"}
    Tests -- "No" --> Block
    Tests -- "Yes" --> Merge["Merge"]
```

Next: [ADR-0001](../07-decisions/adr-0001-thin-paypal-client.md) →
