import dayjs from 'dayjs'
import { sanitize } from '../lib/sanitize'

interface Props {
  message: any
  onEdit: (msg: any) => void
}

export function StudentCard({ message, onEdit }: Props) {
  const meta = message.meta || {}
  return (
    <div className="border rounded p-3 bg-white shadow-sm flex flex-col justify-between">
      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold">{message.student_name}</h3>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-200">{message.source === 'manual' ? 'עריכה ידנית' : 'אוטומטי'}</span>
        </div>
        <div className="text-xs text-gray-500 mb-2">
          נוצר: {dayjs.unix(message.created_at).format('DD.MM.YYYY HH:mm')}<br/>
          עודכן: {dayjs.unix(message.updated_at).format('DD.MM.YYYY HH:mm')}
        </div>
        {meta.gap !== undefined && (
          <div className="text-xs mb-2">
            פער: <span className={meta.gap > 0 ? 'text-red-600' : 'text-green-600'}>{meta.gap}</span>
            {meta.gap_change !== undefined && meta.gap_change !== null && (
              <span className="ml-1">({meta.gap_change > 0 ? '+' : ''}{meta.gap_change})</span>
            )}
          </div>
        )}
        <div className="text-sm prose prose-sm max-h-32 overflow-hidden" dangerouslySetInnerHTML={{ __html: sanitize(message.content_html) }} />
      </div>
      <div className="text-left mt-2">
        <button className="text-blue-600" onClick={() => onEdit(message)}>עריכה</button>
      </div>
    </div>
  )
}
