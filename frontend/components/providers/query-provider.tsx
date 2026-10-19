"use client"

import { QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import { useState, type ReactNode } from "react"

import { ApiProvider } from "@/components/providers/api-provider"
import { getQueryClient } from "@/lib/query/client"

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(getQueryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider>
        {children}
        <ReactQueryDevtools initialIsOpen={false} />
      </ApiProvider>
    </QueryClientProvider>
  )
}
