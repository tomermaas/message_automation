import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider } from '@mui/material/styles'
import { theme } from '../theme'
import { MessageEditorModal } from './MessageEditorModal'
import { vi } from 'vitest'
import { act } from 'react'

vi.mock('../hooks/usePatchMessage', () => ({
  usePatchMessage: () => ({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false }),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: () => {}, error: () => {} },
}))

vi.mock('@emoji-mart/react', () => ({
  default: () => <div />,
}))

test('save keeps modal open; save & close closes', async () => {
  const onClose = vi.fn()
  render(
    <ThemeProvider theme={theme}>
      <MessageEditorModal open onClose={onClose} message={{ id: 1, content_json: '' }} />
    </ThemeProvider>
  )
  const user = userEvent.setup()
  await act(async () => {
    await user.click(screen.getByRole('button', { name: 'שמור' }))
  })
  expect(onClose).not.toHaveBeenCalled()
  await act(async () => {
    await user.click(screen.getByRole('button', { name: 'שמור וסגור' }))
  })
  expect(onClose).toHaveBeenCalledTimes(1)
})
