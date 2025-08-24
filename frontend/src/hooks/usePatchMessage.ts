import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'

export function usePatchMessage(course_id?: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.patchMessage(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['messages'] })
    },
    meta: { course_id },
  })
}
