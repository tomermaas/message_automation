import { useEffect, useState } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, IconButton, Tooltip, Select, MenuItem, Popover } from '@mui/material'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import { Extension } from '@tiptap/core'
import { usePatchMessage } from '../hooks/usePatchMessage'
import toast from 'react-hot-toast'
import { FormatBold, FormatItalic, FormatUnderlined, FormatColorText, EmojiEmotions, Undo, Redo } from '@mui/icons-material'
import data from '@emoji-mart/data'
import { Picker } from 'emoji-mart'

const FontSize = Extension.create({
  name: 'fontSize',
  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: element => element.style.fontSize,
            renderHTML: attributes => {
              if (!attributes.fontSize) return {}
              return { style: `font-size: ${attributes.fontSize}` }
            },
          },
        },
      },
    ]
  },
  addCommands() {
    return {
      setFontSize:
        size => ({ chain }) => chain().setMark('textStyle', { fontSize: size }).run(),
    }
  },
})

interface Props {
  open: boolean
  onClose: () => void
  message: any | null
}

export function MessageEditorModal({ open, onClose, message }: Props) {
  const patch = usePatchMessage()
  const [colorAnchor, setColorAnchor] = useState<HTMLElement | null>(null)
  const [emojiAnchor, setEmojiAnchor] = useState<HTMLElement | null>(null)
  const [fontSize, setFontSize] = useState('16px')

  const editor = useEditor({
    extensions: [StarterKit, Underline, TextStyle, Color, FontSize],
    content: message?.content_json || '',
  })

  useEffect(() => {
    if (open && message && editor) {
      editor.commands.setContent(message.content_json)
    }
  }, [open, message, editor])

  const handleSave = async (closeAfter: boolean) => {
    if (!editor || !message) return
    const dataPayload = {
      content_html: editor.getHTML(),
      content_json: editor.getJSON(),
      editor_version: 'tiptap-2',
    }
    try {
      await patch.mutateAsync({ id: message.id, data: dataPayload })
      toast.success('נשמר')
      if (closeAfter) onClose()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (!open || !message) return null

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" aria-labelledby="edit-title">
      <DialogTitle id="edit-title">עריכת הודעה</DialogTitle>
      <DialogContent>
        {editor && (
          <Stack direction="row" spacing={1} mb={2}>
            <Tooltip title="מודגש"><IconButton onClick={() => editor.chain().focus().toggleBold().run()} color={editor.isActive('bold') ? 'primary' : 'default'}><FormatBold /></IconButton></Tooltip>
            <Tooltip title="נטוי"><IconButton onClick={() => editor.chain().focus().toggleItalic().run()} color={editor.isActive('italic') ? 'primary' : 'default'}><FormatItalic /></IconButton></Tooltip>
            <Tooltip title="קו תחתי"><IconButton onClick={() => editor.chain().focus().toggleUnderline().run()} color={editor.isActive('underline') ? 'primary' : 'default'}><FormatUnderlined /></IconButton></Tooltip>
            <Tooltip title="צבע טקסט"><IconButton onClick={e => setColorAnchor(e.currentTarget)}><FormatColorText /></IconButton></Tooltip>
            <Popover open={Boolean(colorAnchor)} anchorEl={colorAnchor} onClose={() => setColorAnchor(null)} anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}>
              <input type="color" onChange={e => editor.chain().focus().setColor(e.target.value).run()} />
            </Popover>
            <Select size="small" value={fontSize} onChange={e => { const v = e.target.value as string; setFontSize(v); editor.chain().focus().setFontSize(v).run() }}>
              <MenuItem value="14px">קטן</MenuItem>
              <MenuItem value="16px">רגיל</MenuItem>
              <MenuItem value="20px">גדול</MenuItem>
            </Select>
            <Tooltip title="אימוג'י"><IconButton onClick={e => setEmojiAnchor(e.currentTarget)}><EmojiEmotions /></IconButton></Tooltip>
            <Popover open={Boolean(emojiAnchor)} anchorEl={emojiAnchor} onClose={() => setEmojiAnchor(null)} anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}>
              <Picker data={data} onEmojiSelect={(e: any) => { editor.chain().focus().insertContent(e.native).run(); setEmojiAnchor(null) }} />
            </Popover>
            <Tooltip title="בטל"><IconButton onClick={() => editor.chain().focus().undo().run()}><Undo /></IconButton></Tooltip>
            <Tooltip title="בצע מחדש"><IconButton onClick={() => editor.chain().focus().redo().run()}><Redo /></IconButton></Tooltip>
          </Stack>
        )}
        <div dir="rtl" style={{ border: '1px solid #ccc', borderRadius: 4, padding: 8, minHeight: 240 }}>
          <EditorContent editor={editor} />
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>בטל</Button>
        <Button onClick={() => handleSave(false)} disabled={patch.isPending}>שמור</Button>
        <Button variant="contained" onClick={() => handleSave(true)} disabled={patch.isPending}>שמור וסגור</Button>
      </DialogActions>
    </Dialog>
  )
}
