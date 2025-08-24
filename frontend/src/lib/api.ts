export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8765'

async function request(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    },
    ...opts,
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export const api = {
  status: () => request('/status'),
  login: (username: string, password: string) =>
    request('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request('/logout', { method: 'POST' }),
  courses: () => request('/courses'),
  selectCourse: (course_id: number) =>
    request('/select_course', { method: 'POST', body: JSON.stringify({ course_id }) }),
  messageTypes: (course_id: number) => request(`/message_types?course_id=${course_id}`),
  messages: (params: { course_id: number; type?: string; search?: string; page?: number; limit?: number }) => {
    const q = new URLSearchParams()
    q.set('course_id', String(params.course_id))
    if (params.type && params.type !== 'all') q.set('type', params.type)
    if (params.search) q.set('search', params.search)
    if (params.page) q.set('page', String(params.page))
    if (params.limit) q.set('limit', String(params.limit))
    return request(`/messages?${q.toString()}`)
  },
  patchMessage: (id: number, data: any) =>
    request(`/messages/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}
