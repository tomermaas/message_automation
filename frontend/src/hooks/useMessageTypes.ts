import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useMessageTypes(course_id?: number) {
  return useQuery({
    queryKey: ['message_types', course_id],
    queryFn: () => api.messageTypes(course_id!),
    enabled: !!course_id,
  })
}
