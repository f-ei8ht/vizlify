"use client"

import { useAuth } from "@clerk/nextjs"
import { createContext, useContext, useMemo, type ReactNode } from "react"

import { createApiClient, type ApiClient } from "@/lib/api/client"

const ApiClientContext = createContext<ApiClient | null>(null)

/**
 * Builds the API client once per session and hands it to every query hook.
 * The Clerk token is attached per request; `AUTH_MODE=dev` on the backend
 * simply ignores it.
 */
export function ApiProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth()

  const client = useMemo(
    () => createApiClient({ getToken: () => getToken() }),
    [getToken],
  )

  return (
    <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>
  )
}

export function useApiClient(): ApiClient {
  const client = useContext(ApiClientContext)
  if (!client) {
    throw new Error("useApiClient must be used inside <ApiProvider>.")
  }
  return client
}
