import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useCourses() {
  return useQuery({ queryKey: ['courses'], queryFn: api.courses })
}
