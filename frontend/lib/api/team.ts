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
  TeamMember,
  TeamMemberCreateInput,
  TeamMemberUpdateInput,
} from "@/lib/api/types"

export const teamKeys = {
  all: ["team"] as const,
  byProject: (projectId: string) =>
    [...teamKeys.all, "project", projectId] as const,
  details: () => [...teamKeys.all, "detail"] as const,
  detail: (id: string) => [...teamKeys.details(), id] as const,
}

export const teamQueries = {
  list: (api: ApiClient, projectId: string) =>
    queryOptions({
      queryKey: teamKeys.byProject(projectId),
      queryFn: ({ signal }) =>
        api.get<TeamMember[]>(`/projects/${projectId}/team`, signal),
      enabled: projectId.length > 0,
    }),
}

function patchTeamList(
  queryClient: QueryClient,
  projectId: string,
  id: string,
  patch: Partial<TeamMember>,
): void {
  queryClient.setQueryData<TeamMember[]>(teamKeys.byProject(projectId), (members) =>
    members?.map((member) =>
      member.id === id ? { ...member, ...patch } : member,
    ),
  )
}

export function useTeamMembers(projectId: string) {
  const api = useApiClient()
  return useQuery(teamQueries.list(api, projectId))
}

export function useCreateTeamMember(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: TeamMemberCreateInput) =>
      api.post<TeamMember>(`/projects/${projectId}/team`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: teamKeys.byProject(projectId),
      })
    },
  })
}

export function useUpdateTeamMember(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: TeamMemberUpdateInput }) =>
      api.patch<TeamMember>(`/team/${id}`, input),
    onMutate: async ({ id, input }) => {
      await queryClient.cancelQueries({
        queryKey: teamKeys.byProject(projectId),
      })

      const previousList = queryClient.getQueryData<TeamMember[]>(
        teamKeys.byProject(projectId),
      )
      patchTeamList(queryClient, projectId, id, input)

      return { previousList }
    },
    onError: (_error, _variables, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(
          teamKeys.byProject(projectId),
          context.previousList,
        )
      }
    },
    onSuccess: (member) => {
      patchTeamList(queryClient, projectId, member.id, member)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: teamKeys.byProject(projectId),
      })
    },
  })
}

export function useDeleteTeamMember(projectId: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.delete(`/team/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({
        queryKey: teamKeys.byProject(projectId),
      })

      const previousList = queryClient.getQueryData<TeamMember[]>(
        teamKeys.byProject(projectId),
      )
      queryClient.setQueryData<TeamMember[]>(
        teamKeys.byProject(projectId),
        (members) => members?.filter((member) => member.id !== id),
      )

      return { previousList }
    },
    onError: (_error, _id, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(
          teamKeys.byProject(projectId),
          context.previousList,
        )
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: teamKeys.byProject(projectId),
      })
    },
  })
}
