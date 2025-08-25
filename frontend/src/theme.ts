import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  direction: 'rtl',
  palette: {
    primary: { main: '#2962FF' },
    secondary: { main: '#00BFA5' },
    background: { default: '#FAFAFC', paper: '#FFFFFF' },
  },
  typography: {
    fontFamily: '"Heebo", "Rubik", "Inter", system-ui, sans-serif',
  },
  shape: { borderRadius: 8 },
})
