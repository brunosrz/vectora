import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listApiKeys, createApiKey, revokeApiKey } from '#/server/fns/api-keys'

export const API_KEYS_QUERY_KEY = ['api-keys'] as const

export function useApiKeys() {
  return useQuery({
    queryKey: API_KEYS_QUERY_KEY,
    queryFn: () => listApiKeys(),
    staleTime: 60_000,
  })
}

export function useCreateApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      name: string
      scopes: ('read' | 'write' | 'admin')[]
    }) => createApiKey({ data: input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: API_KEYS_QUERY_KEY }),
  })
}

export function useRevokeApiKey() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => revokeApiKey({ data: { id } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: API_KEYS_QUERY_KEY }),
  })
}
