import { useCourses } from '../hooks/useCourses'
import { useMessageTypes } from '../hooks/useMessageTypes'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

interface Props {
  courseId: number | undefined
  setCourseId: (id: number) => void
  typeFilter: string
  setTypeFilter: (t: string) => void
  search: string
  setSearch: (s: string) => void
  onRefresh: () => void
}

export function FilterBar({ courseId, setCourseId, typeFilter, setTypeFilter, search, setSearch, onRefresh }: Props) {
  const courses = useCourses()
  const types = useMessageTypes(courseId)

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 bg-white shadow">
      <button className="px-2 py-1 border rounded" onClick={() => api.logout().then(() => window.location.href = '/')}>התנתק</button>
      <select
        className="border rounded p-1"
        value={courseId ?? ''}
        onChange={e => {
          const id = Number(e.target.value)
          setCourseId(id)
          api.selectCourse(id).then(() => onRefresh()).catch(err => toast.error(err.message))
        }}
      >
        <option value="">בחר קורס</option>
        {courses.data?.data?.map((c: any) => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
      <select className="border rounded p-1" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
        <option value="all">הכל</option>
        {types.data?.types?.map((t: string) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <input className="border rounded p-1" placeholder="חיפוש" value={search} onChange={e => setSearch(e.target.value)} />
      <button className="px-2 py-1 border rounded" onClick={onRefresh}>רענן</button>
    </div>
  )
}
