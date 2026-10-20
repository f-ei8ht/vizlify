# License and notices

> [Handbook index](../README.md) · [Part 9](./README.md) · **Status: Implemented**

## Project license

Vizlify's source code is released under the **MIT License**. See
[LICENSE](../../LICENSE). You may use, copy, modify, merge, publish, distribute,
sublicense and sell copies, provided the copyright notice and permission notice
are included.

## Third-party software

| Dependency | License | Use |
|------------|---------|-----|
| Next.js, React | MIT | Frontend runtime |
| TanStack Query | MIT | Server-state cache |
| Tailwind CSS | MIT | Styling |
| shadcn/ui | MIT | UI components copied into the repo |
| Base UI | MIT | Headless primitives |
| lucide-react | ISC | Icons |
| next-themes | MIT | Dark mode |
| Clerk SDKs | MIT | Authentication client and backend verification |
| FastAPI | MIT | HTTP framework |
| Pydantic / pydantic-settings | MIT | Validation and config |
| SQLAlchemy | MIT | ORM |
| Alembic | MIT | Migrations |
| asyncpg | Apache-2.0 | PostgreSQL driver |
| httpx | BSD-3-Clause | HTTP client |
| uvicorn | BSD-3-Clause | ASGI server |
| pytest, pytest-asyncio, pytest-cov | MIT / Apache-2.0 | Testing |
| ruff | MIT | Linting |
| PostgreSQL | PostgreSQL License | Database |
| Docker images | various | Runtime packaging |

The authoritative list is in `backend/uv.lock` and `frontend/bun.lock`. When
adding a dependency, check its license and record it on this page if it is not
permissive.

## Commercial tools

**AG Studio (AG Grid)** is a commercial product with its own license. It is not
covered by Vizlify's MIT license. Running the full Money Board requires a
separate AG Studio key. Until that key is configured, the dashboard uses plain
components and the Studio agent is disabled.

**APIMatic** is used as a documentation and integration reference. Its generated
output and hosted services carry their own terms.

**Render** hosts the demo under its own terms. Secrets and data are subject to
Render's platform policies.

## Trademarks

Vizlify is an independent hackathon project. It is **not affiliated with or
endorsed by PayPal**. PayPal, the PayPal logo and related marks belong to
PayPal, Inc. Clerk, AG Grid, APIMatic, Render and Cerebras are trademarks of
their respective owners.

Use of a name in this documentation is descriptive and does not imply
endorsement.

## Sandbox disclaimer

The hackathon build uses PayPal's **sandbox**. No real money moves. Demo
accounts, clients and freelancers are fictional. Do not enter real client data,
real bank details or production credentials into the demo.

## Contributions

By contributing, you agree that your contribution is licensed under the MIT
License and that you have the right to submit it. See
[Contributing](./contributing.md).

Next: [Handbook index](../README.md) →
