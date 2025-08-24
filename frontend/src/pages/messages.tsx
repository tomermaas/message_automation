import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppShell } from '../components/AppShell'
import { FilterBar } from '../components/FilterBar'
import { StudentCard } from '../components/StudentCard'
import { EditMessageDialog } from '../components/EditMessageDialog'
import { useStatus } from '../hooks/useStatus'
import { useMessages } from '../hooks/useMessages'

export default function MessagesPage() {
  const nav = useNavigate()
  const status = useStatus()
  const [courseId, setCourseId] = useState<number | undefined>(undefined)
  const [typeFilter, setTypeFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<any | null>(null)

  useEffect(() => {
    if (!status.data?.logged_in) nav('/')
    else if (status.data?.selected_id) setCourseId(status.data.selected_id)
  }, [status.data, nav])

  const messages = useMessages({ course_id: courseId, type: typeFilter, search })

  return (
    <AppShell>
      <FilterBar
        courseId={courseId}
        setCourseId={setCourseId}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        search={search}
        setSearch={setSearch}
        onRefresh={() => messages.refetch()}
      />
      <div className="p-4 grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px,1fr))' }}>
        {messages.data?.data?.map((m: any) => (
          <StudentCard key={m.id} message={m} onEdit={setEditing} />
        ))}
      </div>
      <EditMessageDialog open={!!editing} onClose={() => setEditing(null)} message={editing} />
    </AppShell>
  )
}
