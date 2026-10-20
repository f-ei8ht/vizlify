import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type { Action, ActionStatus } from "@/lib/api/types"

export const actionKeys = {
  all: ["actions"] as const,
  lists: () => [...actionKeys.all, "list"] as const,
  list: (status?: ActionStatus) =>
    [...actionKeys.lists(), status ?? "all"] as const,
  details: () => [...actionKeys.all, "detail"] as const,
  detail: (id: string) => [...actionKeys.details(), id] as const,
}

export const actionQueries = {
  list: (api: ApiClient, status?: ActionStatus) =>
    queryOptions({
      queryKey: actionKeys.list(status),
      queryFn: ({ signal }) =>
        api.get<Action[]>(
          status ? `/actions?status=${status}` : "/actions",
          signal,
        ),
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: actionKeys.detail(id),
      queryFn: ({ signal }) => api.get<Action>(`/actions/${id}`, signal),
      enabled: id.length > 0,
    }),
}

/** An approval can create an invoice or a payout; refresh the money views too. */
function invalidateAfterDecision(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: ["actions"] })
  void queryClient.invalidateQueries({ queryKey: ["invoices"] })
  void queryClient.invalidateQueries({ queryKey: ["payouts"] })
  void queryClient.invalidateQueries({ queryKey: ["projects"] })
}

export function useActions(status?: ActionStatus) {
  const api = useApiClient()
  return useQuery(actionQueries.list(api, status))
}

export function useAction(id: string) {
  const api = useApiClient()
  return useQuery(actionQueries.detail(api, id))
}

export function useApproveAction() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Action>(`/actions/${id}/approve`, {}),
    onSuccess: (action) => {
      queryClient.setQueryData(actionKeys.detail(action.id), action)
      invalidateAfterDecision(queryClient)
    },
  })
}

export function useRejectAction() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post<Action>(`/actions/${id}/reject`, { reason }),
    onSuccess: (action) => {
      queryClient.setQueryData(actionKeys.detail(action.id), action)
      invalidateAfterDecision(queryClient)
    },
  })
}
