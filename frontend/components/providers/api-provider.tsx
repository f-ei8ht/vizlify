"use client"

import { useAuth } from "@clerk/nextjs"
import { createContext, useContext, useMemo, type ReactNode } from "react"

import { createApiClient, type ApiClient, type TokenGetter } from "@/lib/api/client"

const ApiClientContext = createContext<ApiClient | null>(null)

/**
 * Builds the API client once per session and hands it to every query hook.
 * Clerk is optional: in AUTH_MODE=dev the backend ignores the token, so a
 * key-free local run must not require a Clerk provider at all.
 */
export function ApiProvider({ children }: { children: ReactNode }) {
  const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY)

  if (!clerkEnabled) {
    return <ClientProvider>{children}</ClientProvider>
  }
  return <ClerkClientProvider>{children}</ClerkClientProvider>
}

function ClerkClientProvider({ children }: { children: ReactNode }) {
  const { getToken } = useAuth()
  const getTokenCallback = useMemo(() => () => getToken(), [getToken])

  return <ClientProvider getToken={getTokenCallback}>{children}</ClientProvider>
}

function ClientProvider({
  getToken,
  children,
}: {
  getToken?: TokenGetter
  children: ReactNode
}) {
  const client = useMemo(() => createApiClient({ getToken }), [getToken])

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
