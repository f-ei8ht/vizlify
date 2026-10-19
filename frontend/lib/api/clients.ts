import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type { Client, ClientCreateInput, ClientUpdateInput } from "@/lib/api/types"

export const clientKeys = {
  all: ["clients"] as const,
  lists: () => [...clientKeys.all, "list"] as const,
  list: () => [...clientKeys.lists()] as const,
  details: () => [...clientKeys.all, "detail"] as const,
  detail: (id: string) => [...clientKeys.details(), id] as const,
}

export const clientQueries = {
  list: (api: ApiClient) =>
    queryOptions({
      queryKey: clientKeys.list(),
      queryFn: ({ signal }) => api.get<Client[]>("/clients", signal),
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: clientKeys.detail(id),
      queryFn: ({ signal }) => api.get<Client>(`/clients/${id}`, signal),
      enabled: id.length > 0,
    }),
}

function patchClientList(
  queryClient: QueryClient,
  id: string,
  patch: Partial<Client>,
): void {
  queryClient.setQueryData<Client[]>(clientKeys.list(), (clients) =>
    clients?.map((client) => (client.id === id ? { ...client, ...patch } : client)),
  )
}

export function useClients() {
  const api = useApiClient()
  return useQuery(clientQueries.list(api))
}

export function useClient(id: string) {
  const api = useApiClient()
  return useQuery(clientQueries.detail(api, id))
}

export function useCreateClient() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: ClientCreateInput) => api.post<Client>("/clients", input),
    onSuccess: (client) => {
      queryClient.setQueryData(clientKeys.detail(client.id), client)
      void queryClient.invalidateQueries({ queryKey: clientKeys.lists() })
    },
  })
}

export function useUpdateClient(id: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: ClientUpdateInput) =>
      api.patch<Client>(`/clients/${id}`, input),
    onMutate: async (input) => {
      await queryClient.cancelQueries({ queryKey: clientKeys.detail(id) })

      const previousDetail = queryClient.getQueryData<Client>(clientKeys.detail(id))
      const previousList = queryClient.getQueryData<Client[]>(clientKeys.list())

      if (previousDetail) {
        queryClient.setQueryData(clientKeys.detail(id), { ...previousDetail, ...input })
      }
      patchClientList(queryClient, id, input)

      return { previousDetail, previousList }
    },
    onError: (_error, _input, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(clientKeys.detail(id), context.previousDetail)
      }
      if (context?.previousList) {
        queryClient.setQueryData(clientKeys.list(), context.previousList)
      }
    },
    onSuccess: (client) => {
      queryClient.setQueryData(clientKeys.detail(client.id), client)
      patchClientList(queryClient, client.id, client)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: clientKeys.detail(id) })
      void queryClient.invalidateQueries({ queryKey: clientKeys.lists() })
    },
  })
}

export function useDeleteClient() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.delete(`/clients/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: clientKeys.lists() })

      const previousList = queryClient.getQueryData<Client[]>(clientKeys.list())
      queryClient.setQueryData<Client[]>(clientKeys.list(), (clients) =>
        clients?.filter((client) => client.id !== id),
      )

      return { previousList }
    },
    onError: (_error, _id, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(clientKeys.list(), context.previousList)
      }
    },
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: clientKeys.detail(id) })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: clientKeys.lists() })
    },
  })
}
