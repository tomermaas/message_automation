import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useStatus } from './useStatus'

export function useCourses() {
  const status = useStatus()
  return useQuery({
    queryKey: ['courses'],
    queryFn: api.courses,
    enabled: status.data?.logged_in,
  })
}
