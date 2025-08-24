import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useStatus() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['status'], queryFn: api.status })
  return { ...q, refetch: () => qc.invalidateQueries({ queryKey: ['status'] }) }
}
