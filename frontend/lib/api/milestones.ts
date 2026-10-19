import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query"

import { useApiClient } from "@/components/providers/api-provider"
import type { ApiClient } from "@/lib/api/client"
import type {
  Milestone,
  MilestoneCreateInput,
  MilestoneUpdateInput,
} from "@/lib/api/types"

export const milestoneKeys = {
  all: ["milestones"] as const,
  byProject: (projectId: string) =>
    [...milestoneKeys.all, "project", projectId] as const,
  details: () => [...milestoneKeys.all, "detail"] as const,
  detail: (id: string) => [...milestoneKeys.details(), id] as const,
}

export const milestoneQueries = {
  list: (api: ApiClient, projectId: string) =>
    queryOptions({
      queryKey: milestoneKeys.byProject(projectId),
      queryFn: ({ signal }) =>
        api.get<Milestone[]>(`/projects/${projectId}/milestones`, signal),
      enabled: projectId.length > 0,
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: milestoneKeys.detail(id),
      queryFn: ({ signal }) => api.get<Milestone>(`/milestones/${id}`, signal),
      enabled: id.length > 0,
    }),
}

function patchMilestoneList(
  queryClient: QueryClient,
  projectId: string,
  id: string,
  patch: Partial<Milestone>,
): void {
  queryClient.setQueryData<Milestone[]>(
    milestoneKeys.byProject(projectId),
    (milestones) =>
      milestones?.map((milestone) =>
        milestone.id === id ? { ...milestone, ...patch } : milestone,
      ),
  )
}

export function useMilestones(projectId: string) {
  const api = useApiClient()
  return useQuery(milestoneQueries.list(api, projectId))
}

export function useMilestone(id: string) {
  const api = useApiClient()
  return useQuery(milestoneQueries.detail(api, id))
}

export function useCreateMilestone(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: MilestoneCreateInput) =>
      api.post<Milestone>(`/projects/${projectId}/milestones`, input),
    onSuccess: (milestone) => {
      queryClient.setQueryData(milestoneKeys.detail(milestone.id), milestone)
      void queryClient.invalidateQueries({
        queryKey: milestoneKeys.byProject(projectId),
      })
    },
  })
}

export function useUpdateMilestone(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: MilestoneUpdateInput }) =>
      api.patch<Milestone>(`/milestones/${id}`, input),
    onMutate: async ({ id, input }) => {
      await queryClient.cancelQueries({
        queryKey: milestoneKeys.byProject(projectId),
      })

      const previousList = queryClient.getQueryData<Milestone[]>(
        milestoneKeys.byProject(projectId),
      )
      const previousDetail = queryClient.getQueryData<Milestone>(
        milestoneKeys.detail(id),
      )

      patchMilestoneList(queryClient, projectId, id, input)
      if (previousDetail) {
        queryClient.setQueryData(milestoneKeys.detail(id), {
          ...previousDetail,
          ...input,
        })
      }

      return { previousList, previousDetail }
    },
    onError: (_error, _variables, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(
          milestoneKeys.byProject(projectId),
          context.previousList,
        )
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(
          milestoneKeys.detail(context.previousDetail.id),
          context.previousDetail,
        )
      }
    },
    onSuccess: (milestone) => {
      queryClient.setQueryData(milestoneKeys.detail(milestone.id), milestone)
      patchMilestoneList(queryClient, projectId, milestone.id, milestone)
    },
    onSettled: (_data, _error, { id }) => {
      void queryClient.invalidateQueries({
        queryKey: milestoneKeys.byProject(projectId),
      })
      void queryClient.invalidateQueries({ queryKey: milestoneKeys.detail(id) })
    },
  })
}

export function useDeleteMilestone(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.delete(`/milestones/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({
        queryKey: milestoneKeys.byProject(projectId),
      })

      const previousList = queryClient.getQueryData<Milestone[]>(
        milestoneKeys.byProject(projectId),
      )
      queryClient.setQueryData<Milestone[]>(
        milestoneKeys.byProject(projectId),
        (milestones) => milestones?.filter((milestone) => milestone.id !== id),
      )

      return { previousList }
    },
    onError: (_error, _id, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(
          milestoneKeys.byProject(projectId),
          context.previousList,
        )
      }
    },
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: milestoneKeys.detail(id) })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: milestoneKeys.byProject(projectId),
      })
    },
  })
}
