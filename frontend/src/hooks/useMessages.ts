import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useMessages(params: { course_id?: number; type?: string; search?: string }) {
  return useInfiniteQuery({
    queryKey: ['messages', params],
    queryFn: ({ pageParam = 1 }) =>
      api.messages({ course_id: params.course_id, type: params.type, search: params.search, page: pageParam }),
    getNextPageParam: lastPage => {
      const { page, limit, total } = lastPage
      return page * limit < total ? page + 1 : undefined
    },
    enabled: params.course_id != null,
  })
}

