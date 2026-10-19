import { queryOptions, useQuery } from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type { Account } from "@/lib/api/types"

export const accountKeys = {
  all: ["account"] as const,
  me: () => [...accountKeys.all, "me"] as const,
}

export const accountQueries = {
  me: (api: ApiClient) =>
    queryOptions({
      queryKey: accountKeys.me(),
      queryFn: ({ signal }) => api.get<Account>("/me", signal),
      staleTime: 5 * 60_000,
    }),
}

export function useMe() {
  const api = useApiClient()
  return useQuery(accountQueries.me(api))
}
