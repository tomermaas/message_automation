import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { DbTypeSelect } from './DbTypeSelect'
import { ThemeProvider } from '@mui/material/styles'
import { theme } from '../theme'
import { useState } from 'react'
import { act } from 'react-dom/test-utils'

function Wrapper() {
  const [val, setVal] = useState('all')
  return <DbTypeSelect value={val} onChange={setVal} />
}

test('db_type dropdown options and URL sync', async () => {
  const user = userEvent.setup()
  render(
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <Wrapper />
      </BrowserRouter>
    </ThemeProvider>
  )
  const select = screen.getByLabelText('סוג הודעה')
  await act(async () => {
    await user.click(select)
  })
  expect(screen.getByRole('option', { name: 'הכל' })).toBeInTheDocument()
  expect(screen.getByRole('option', { name: 'מרחק מציון יעד' })).toBeInTheDocument()
  await act(async () => {
    await user.click(screen.getByRole('option', { name: 'מרחק מציון יעד' }))
  })
  expect(window.location.search).toBe('?db_type=distance')
})
