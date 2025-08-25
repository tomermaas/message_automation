import { useEffect, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import { baseEditorOptions } from '../lib/tiptap/editor'
import { usePatchMessage } from '../hooks/usePatchMessage'
import toast from 'react-hot-toast'

interface Props {
  open: boolean
  onClose: () => void
  message: any | null
}

export function EditMessageDialog({ open, onClose, message }: Props) {
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const patch = usePatchMessage()

  const editor = useEditor({
    ...baseEditorOptions,
    content: message?.content_json || '',
  })

  useEffect(() => {
    if (open && message && editor) {
      editor.commands.setContent(message.content_json)
    }
  }, [open, message, editor])

  // autosave
  useEffect(() => {
    if (!open || !editor || !message) return
    const interval = setInterval(() => {
      const current = editor.getJSON()
      if (JSON.stringify(current) !== JSON.stringify(message.content_json)) {
        save(true)
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [open, editor, message])

  async function save(silent = false) {
    if (!editor || !message) return
    const json = editor.getJSON()
    const html = editor.getHTML()
    try {
      await patch.mutateAsync({
        id: message.id,
        data: { content_html: html, content_json: json, editor_version: 'tiptap-2' },
      })
      setLastSaved(new Date())
      if (!silent) {
        toast.success('נשמר')
        onClose()
      }
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (!open || !message) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center">
      <div className="bg-white p-4 rounded w-full max-w-2xl">
        <h2 className="mb-2">עריכת הודעה ל{message.student_name}</h2>
        {editor && (
          <div className="flex flex-wrap gap-2 mb-2 border-b pb-2">
            <button
              className={editor.isActive('bold') ? 'font-bold bg-gray-200 px-2 py-1 rounded' : 'px-2 py-1 rounded'}
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              B
            </button>
            <button
              className={editor.isActive('italic') ? 'italic bg-gray-200 px-2 py-1 rounded' : 'italic px-2 py-1 rounded'}
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              I
            </button>
            <button
              className={editor.isActive('underline') ? 'underline bg-gray-200 px-2 py-1 rounded' : 'underline px-2 py-1 rounded'}
              onClick={() => editor.chain().focus().toggleUnderline().run()}
            >
              U
            </button>
            <button
              className={editor.isActive('bulletList') ? 'bg-gray-200 px-2 py-1 rounded' : 'px-2 py-1 rounded'}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
              •
            </button>
            <button
              className={editor.isActive('orderedList') ? 'bg-gray-200 px-2 py-1 rounded' : 'px-2 py-1 rounded'}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
              1.
            </button>
          </div>
        )}
        <div className="border rounded mb-2 p-2 max-h-96 overflow-y-auto">
          <EditorContent editor={editor} />
        </div>
        {lastSaved && (
          <div className="text-xs text-gray-500 mb-2">נשמר אוטומטית לפני {Math.floor((Date.now()-lastSaved.getTime())/1000)} שניות</div>
        )}
        <div className="flex justify-end gap-2">
          <button className="px-3 py-1 border rounded" onClick={onClose}>ביטול</button>
          <button className="px-3 py-1 border rounded bg-blue-600 text-white" onClick={save}>שמור</button>
        </div>
      </div>
    </div>
  )
}
