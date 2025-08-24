import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import Link from '@tiptap/extension-link'
import TextAlign from '@tiptap/extension-text-align'
import { EditorOptions } from '@tiptap/react'

export const editorExtensions = [
  StarterKit,
  Underline,
  Link.configure({ openOnClick: false }),
  TextAlign.configure({ types: ['heading', 'paragraph'] }),
]

export const baseEditorOptions: Partial<EditorOptions> = {
  extensions: editorExtensions,
  content: '',
}
