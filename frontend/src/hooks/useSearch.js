import { useQuery } from '@tanstack/react-query'
import { searchMachines, getMachine, getFilters, getSuggestions } from '../api/client'

export function useSearchResults(params) {
  return useQuery({
    queryKey: ['search', params],
    queryFn: () => searchMachines(params),
    staleTime: 2 * 60 * 1000,
    placeholderData: (prev) => prev,
  })
}

export function useMachine(id) {
  return useQuery({
    queryKey: ['machine', id],
    queryFn: () => getMachine(id),
    enabled: !!id,
  })
}

export function useFilters() {
  return useQuery({
    queryKey: ['filters'],
    queryFn: getFilters,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSuggestions(q) {
  return useQuery({
    queryKey: ['suggestions', q],
    queryFn: () => getSuggestions(q),
    enabled: typeof q === 'string' && q.length >= 2,
    staleTime: 60 * 1000,
  })
}
