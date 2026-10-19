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
  Project,
  ProjectCreateInput,
  ProjectUpdateInput,
} from "@/lib/api/types"

export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: () => [...projectKeys.lists()] as const,
  details: () => [...projectKeys.all, "detail"] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
}

export const projectQueries = {
  list: (api: ApiClient) =>
    queryOptions({
      queryKey: projectKeys.list(),
      queryFn: ({ signal }) => api.get<Project[]>("/projects", signal),
    }),
  detail: (api: ApiClient, id: string) =>
    queryOptions({
      queryKey: projectKeys.detail(id),
      queryFn: ({ signal }) => api.get<Project>(`/projects/${id}`, signal),
      enabled: id.length > 0,
    }),
}

function patchProjectList(
  queryClient: QueryClient,
  id: string,
  patch: Partial<Project>,
): void {
  queryClient.setQueryData<Project[]>(projectKeys.list(), (projects) =>
    projects?.map((project) =>
      project.id === id ? { ...project, ...patch } : project,
    ),
  )
}

export function useProjects() {
  const api = useApiClient()
  return useQuery(projectQueries.list(api))
}

export function useProject(id: string) {
  const api = useApiClient()
  return useQuery(projectQueries.detail(api, id))
}

export function useCreateProject() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: ProjectCreateInput) =>
      api.post<Project>("/projects", input),
    onSuccess: (project) => {
      queryClient.setQueryData(projectKeys.detail(project.id), project)
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

export function useUpdateProject(id: string) {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: ProjectUpdateInput) =>
      api.patch<Project>(`/projects/${id}`, input),
    onMutate: async (input) => {
      await queryClient.cancelQueries({ queryKey: projectKeys.detail(id) })

      const previousDetail = queryClient.getQueryData<Project>(projectKeys.detail(id))
      const previousList = queryClient.getQueryData<Project[]>(projectKeys.list())

      if (previousDetail) {
        queryClient.setQueryData(projectKeys.detail(id), { ...previousDetail, ...input })
      }
      patchProjectList(queryClient, id, input)

      return { previousDetail, previousList }
    },
    onError: (_error, _input, context) => {
      if (context?.previousDetail) {
        queryClient.setQueryData(projectKeys.detail(id), context.previousDetail)
      }
      if (context?.previousList) {
        queryClient.setQueryData(projectKeys.list(), context.previousList)
      }
    },
    onSuccess: (project) => {
      queryClient.setQueryData(projectKeys.detail(project.id), project)
      patchProjectList(queryClient, project.id, project)
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.detail(id) })
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}

export function useDeleteProject() {
  const api = useApiClient()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${id}`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: projectKeys.lists() })

      const previousList = queryClient.getQueryData<Project[]>(projectKeys.list())
      queryClient.setQueryData<Project[]>(projectKeys.list(), (projects) =>
        projects?.filter((project) => project.id !== id),
      )

      return { previousList }
    },
    onError: (_error, _id, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(projectKeys.list(), context.previousList)
      }
    },
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: projectKeys.detail(id) })
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    },
  })
}
