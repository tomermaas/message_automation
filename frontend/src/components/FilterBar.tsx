import { useCourses } from '../hooks/useCourses'
import { api } from '../lib/api'
import toast from 'react-hot-toast'
import { DbTypeSelect } from './DbTypeSelect'

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

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 bg-white shadow-sm">
      <button
        className="px-3 py-1 border rounded focus-visible:outline-primary focus-visible:outline-2"
        onClick={() => api.logout().then(() => (window.location.href = '/'))}
      >
        התנתק
      </button>
      <select
        className="border rounded p-1 focus-visible:outline-primary focus-visible:outline-2"
        value={courseId ?? ''}
        onChange={e => {
          const id = Number(e.target.value)
          setCourseId(id)
          api
            .selectCourse(id)
            .then(() => onRefresh())
            .catch(err => toast.error(err.message))
        }}
      >
        <option value="">בחר קורס</option>
        {courses.data?.data?.map((c: any) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <DbTypeSelect value={typeFilter} onChange={setTypeFilter} />
      <input
        className="border rounded p-1 focus-visible:outline-primary focus-visible:outline-2"
        placeholder="חיפוש"
        value={search}
        onChange={e => setSearch(e.target.value)}
      />
      <button
        className="px-3 py-1 bg-primary text-white rounded hover:brightness-110 transition focus-visible:outline-primary focus-visible:outline-2"
        onClick={() => {
          onRefresh()
          toast.success('רשימה עודכנה')
        }}
      >
        רענון
      </button>
    </div>
  )
}
