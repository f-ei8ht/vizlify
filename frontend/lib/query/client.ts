import { QueryClient } from "@tanstack/react-query"

import { ApiError } from "@/lib/api/client"

/**
 * Server state lives in the QueryClient — never in a global store.
 * Client-only UI state (open dialogs, form drafts) stays in React state.
 */

export const QUERY_STALE_TIME = 30_000
export const QUERY_GC_TIME = 5 * 60_000

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Data is fresh for 30s; after that it renders as "stale" and
        // refetches in the background on focus/reconnect.
        staleTime: QUERY_STALE_TIME,
        gcTime: QUERY_GC_TIME,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        retry: (failureCount, error) => {
          if (error instanceof ApiError) {
            // Auth, validation and missing-resource errors will not fix
            // themselves by retrying.
            if (error.isUnauthorized || error.isValidation || error.status === 404) {
              return false
            }
          }
          return failureCount < 2
        },
      },
      mutations: {
        retry: false,
      },
    },
  })
}

let browserQueryClient: QueryClient | undefined

/** One QueryClient per browser tab; a fresh one per server render. */
export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    return makeQueryClient()
  }

  browserQueryClient ??= makeQueryClient()
  return browserQueryClient
}
