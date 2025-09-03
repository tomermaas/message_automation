import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { FilterBar } from '../components/FilterBar'
import { StudentCard } from '../components/StudentCard'
import { MessageEditorModal } from '../components/MessageEditorModal'
import { useStatus } from '../hooks/useStatus'
import { useMessages } from '../hooks/useMessages'
import { api } from '../lib/api'

export default function MessagesPage() {
  const nav = useNavigate()
  const [params] = useSearchParams()
  const status = useStatus()
  const [courseId, setCourseId] = useState<number | undefined>(undefined)
  const [typeFilter, setTypeFilter] = useState(params.get('db_type') || 'all')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<any | null>(null)

  const messages = useMessages({ course_id: courseId, type: typeFilter, search })

  useEffect(() => {
    if (!status.data?.logged_in) nav('/')
    else if (status.data?.selected_id && courseId == null) {
      const id = status.data.selected_id
      setCourseId(id)
      api.selectCourse(id).then(() => messages.refetch())
    }
  }, [status.data, nav, courseId])
  const allMessages = messages.data?.pages.flatMap(p => p.data) ?? []

  return (
    <AppShell>
      <button
        onClick={() => api.logout().then(() => nav('/'))}
        className="fixed top-4 right-4 bg-gray-300 px-2 py-1 rounded"
      >
        יציאה
      </button>
      <FilterBar
        courseId={courseId}
        setCourseId={setCourseId}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        search={search}
        setSearch={setSearch}
        onRefresh={() => messages.refetch()}
      />
      <div className="p-4 grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px,1fr))' }}>
        {allMessages.map((m: any) => (
          <StudentCard key={m.id} message={m} onEdit={setEditing} />
        ))}
      </div>
      {messages.hasNextPage && (
        <div className="text-center p-4">
          <button
            className="px-4 py-2 bg-primary text-white rounded hover:brightness-110 transition focus-visible:outline-primary focus-visible:outline-2"
            onClick={() => messages.fetchNextPage()}
            disabled={messages.isFetchingNextPage}
          >
            {messages.isFetchingNextPage ? 'טוען...' : 'טען עוד'}
          </button>
        </div>
      )}
      <MessageEditorModal open={!!editing} onClose={() => setEditing(null)} message={editing} />
    </AppShell>
  )
}
