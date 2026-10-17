# syntax=docker/dockerfile:1

# --- Build ---
FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN bun run build

# --- Runtime ---
FROM oven/bun:1 AS runtime

WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=build --chown=bun:bun /app ./

USER bun
EXPOSE 3000

CMD ["bun", "run", "start"]
