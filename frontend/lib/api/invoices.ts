import { queryOptions, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type { Action, Invoice } from "@/lib/api/types"

export const invoiceKeys = {
  all: ["invoices"] as const,
  lists: () => [...invoiceKeys.all, "list"] as const,
  list: () => [...invoiceKeys.lists()] as const,
  details: () => [...invoiceKeys.all, "detail"] as const,
  detail: (id: string) => [...invoiceKeys.details(), id] as const,
}

export const invoiceQueries = {
  list: (api: ApiClient) =>
    queryOptions({
      queryKey: invoiceKeys.list(),
      queryFn: ({ signal }) => api.get<Invoice[]>("/invoices", signal),
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: invoiceKeys.detail(id),
      queryFn: ({ signal }) => api.get<Invoice>(`/invoices/${id}`, signal),
      enabled: id.length > 0,
    }),
}

export function useInvoices() {
  const api = useApiClient()
  return useQuery(invoiceQueries.list(api))
}

export function useInvoice(id: string) {
  const api = useApiClient()
  return useQuery(invoiceQueries.detail(api, id))
}

export function useProposeInvoice() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (milestoneId: string) =>
      api.post<Action>(`/milestones/${milestoneId}/invoice`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] })
    },
  })
}

export function useRemindInvoice() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Action>(`/invoices/${id}/remind`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] })
    },
  })
}

export function useCancelInvoice() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Action>(`/invoices/${id}/cancel`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] })
    },
  })
}

export function useProposeInvoicePayout() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Action>(`/invoices/${id}/payout`, {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions"] })
    },
  })
}

export function useRefreshInvoice() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.post<Invoice>(`/invoices/${id}/refresh`, {}),
    onSuccess: (invoice) => {
      queryClient.setQueryData(invoiceKeys.detail(invoice.id), invoice)
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.lists() })
    },
  })
}
