import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useMessages(params: { course_id?: number; type?: string; search?: string }) {
  return useQuery({
    queryKey: ['messages', params],
    queryFn: () => api.messages({ course_id: params.course_id!, type: params.type, search: params.search }),
    enabled: !!params.course_id,
  })
}
