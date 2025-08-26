import dayjs from 'dayjs'
import { sanitize } from '../lib/sanitize'

interface Props {
  message: any
  onEdit: (msg: any) => void
}

export function StudentCard({ message, onEdit }: Props) {
  const meta = message.meta || {}
  return (
    <div className="border rounded p-4 bg-white shadow-sm flex flex-col justify-between transition-shadow duration-150 hover:shadow-md focus-within:outline-primary focus-within:outline-2">
      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-text">{message.student_name}</h3>
          <span className={`text-xs px-2 py-0.5 rounded ${message.source === 'manual' ? 'bg-primary/10 text-primary' : 'bg-gray-200 text-gray-700'}`}>{message.source === 'manual' ? 'עריכה ידנית' : 'אוטומטי'}</span>
        </div>
        <div className="text-xs text-gray-500 mb-2">
          נוצר: {dayjs.unix(message.created_at).format('DD.MM.YYYY HH:mm')}<br />
          עודכן: {dayjs.unix(message.updated_at).format('DD.MM.YYYY HH:mm')}
        </div>
        {meta.target_score !== undefined && meta.total_score !== undefined && (
          <div className="text-xs mb-2">
            ציון מבחן: {meta.total_score} | ציון יעד: {meta.target_score}
          </div>
        )}
        {meta.gap !== undefined && (
          <div className="text-xs mb-2">
            פער: <span className={meta.gap > 0 ? 'text-success' : meta.gap < 0 ? 'text-error' : ''}>{meta.gap}</span>
            {meta.gap_change !== undefined && meta.gap_change !== null && (
              <span className="mr-1">({meta.gap_change > 0 ? '+' : ''}{meta.gap_change})</span>
            )}
          </div>
        )}
        <div
          className="text-sm max-h-32 overflow-hidden"
          style={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}
          dangerouslySetInnerHTML={{ __html: sanitize(message.content_html) }}
        />
      </div>
      <div className="text-left mt-2">
        <button className="text-primary focus-visible:outline-primary focus-visible:outline-2" onClick={() => onEdit(message)}>עריכה</button>
      </div>
    </div>
  )
}
