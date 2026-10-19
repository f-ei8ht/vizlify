"use client"

import {
  AlertCircleIcon,
  RefreshCwIcon,
  type LucideIcon,
} from "lucide-react"
import type { ReactNode } from "react"

import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import { ApiError } from "@/lib/api/client"
import { formatTime } from "@/lib/format"

/** The subset of a TanStack Query result these state views need. */
export interface QueryLike<T> {
  data: T | undefined
  error: Error | null
  isPending: boolean
  isError: boolean
  isFetching: boolean
  isStale: boolean
  dataUpdatedAt: number
  refetch: () => unknown
}

/** Fresh / stale / refreshing / cached badge for a single query. */
export function QueryStatus<T>({ query }: { query: QueryLike<T> }) {
  if (query.isPending) {
    return (
      <Badge variant="secondary">
        <Spinner />
        Loading
      </Badge>
    )
  }

  if (query.isError) {
    return <Badge variant="destructive">Cached data</Badge>
  }

  if (query.isFetching) {
    return (
      <Badge variant="secondary">
        <Spinner />
        Refreshing
      </Badge>
    )
  }

  if (query.isStale) {
    return <Badge variant="outline">Stale</Badge>
  }

  return <Badge variant="outline">Fresh</Badge>
}

export function UpdatedAt({ timestamp }: { timestamp: number }) {
  if (!timestamp) return null

  return (
    <span className="text-xs text-muted-foreground">
      Updated {formatTime(timestamp)}
    </span>
  )
}

function errorHint(error: Error): string | null {
  if (!(error instanceof ApiError)) return null
  if (error.isUnauthorized) return "Sign in to load your workspace, then try again."
  if (error.isNetwork) return "Start the API and try again."
  return null
}

export function QueryError({
  error,
  onRetry,
  title = "Couldn't load this data",
}: {
  error: Error
  onRetry: () => void
  title?: string
}) {
  const hint = errorHint(error)

  return (
    <Alert variant="destructive">
      <AlertCircleIcon />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        {error.message}
        {hint ? ` ${hint}` : null}
      </AlertDescription>
      <AlertAction>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCwIcon data-icon="inline-start" />
          Retry
        </Button>
      </AlertAction>
    </Alert>
  )
}

/** Shown when a background refetch fails but the cache still has data. */
export function StaleDataNotice({
  error,
  onRetry,
}: {
  error: Error
  onRetry: () => void
}) {
  return (
    <Alert variant="destructive">
      <AlertCircleIcon />
      <AlertTitle>Couldn&apos;t refresh</AlertTitle>
      <AlertDescription>
        {error.message} Showing the last successful data.
      </AlertDescription>
      <AlertAction>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCwIcon data-icon="inline-start" />
          Retry
        </Button>
      </AlertAction>
    </Alert>
  )
}

export function QueryEmpty({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <Empty className="border">
      <EmptyHeader>
        {Icon ? (
          <EmptyMedia variant="icon">
            <Icon />
          </EmptyMedia>
        ) : null}
        <EmptyTitle>{title}</EmptyTitle>
        {description ? <EmptyDescription>{description}</EmptyDescription> : null}
      </EmptyHeader>
      {action ? <EmptyContent>{action}</EmptyContent> : null}
    </Empty>
  )
}

/**
 * Renders the five server-state shapes consistently:
 * loading (no data), error (no data), empty, background refresh, and stale data
 * (a failed refresh with cached data still on screen).
 */
export function DataState<T>({
  query,
  skeleton,
  empty,
  isEmpty,
  children,
}: {
  query: QueryLike<T>
  skeleton: ReactNode
  empty: ReactNode
  isEmpty?: (data: T) => boolean
  children: (data: T) => ReactNode
}) {
  if (query.isPending) return <>{skeleton}</>

  if (query.isError && query.data === undefined) {
    return (
      <QueryError
        error={query.error ?? new Error("Unknown error")}
        onRetry={() => void query.refetch()}
      />
    )
  }

  if (query.data === undefined) return <>{skeleton}</>

  if (isEmpty?.(query.data)) {
    return (
      <div className="flex flex-col gap-4">
        {query.isError ? (
          <StaleDataNotice
            error={query.error ?? new Error("Unknown error")}
            onRetry={() => void query.refetch()}
          />
        ) : null}
        {empty}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {query.isError ? (
        <StaleDataNotice
          error={query.error ?? new Error("Unknown error")}
          onRetry={() => void query.refetch()}
        />
      ) : null}
      {children(query.data)}
    </div>
  )
}
