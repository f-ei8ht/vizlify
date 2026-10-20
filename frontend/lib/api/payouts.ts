import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type { Action, Payout } from "@/lib/api/types"

export const payoutKeys = {
  all: ["payouts"] as const,
  lists: () => [...payoutKeys.all, "list"] as const,
  list: () => [...payoutKeys.lists()] as const,
  details: () => [...payoutKeys.all, "detail"] as const,
  detail: (id: string) => [...payoutKeys.details(), id] as const,
}

export const payoutQueries = {
  list: (api: ApiClient) =>
    queryOptions({
      queryKey: payoutKeys.list(),
      queryFn: ({ signal }) => api.get<Payout[]>("/payouts", signal),
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: payoutKeys.detail(id),
      queryFn: ({ signal }) => api.get<Payout>(`/payouts/${id}`, signal),
      enabled: id.length > 0,
    }),
}

export function usePayouts() {
  const api = useApiClient()
  return useQuery(payoutQueries.list(api))
}

export function usePayout(id: string) {
  const api = useApiClient()
  return useQuery(payoutQueries.detail(api, id))
}

export function useProposePayoutExecution() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Action>(`/payouts/${id}/execute`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] })
    },
  })
}
