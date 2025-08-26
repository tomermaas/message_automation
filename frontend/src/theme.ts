import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  direction: 'rtl',
  palette: {
    primary: { main: '#5F2EEA' },
    secondary: { main: '#FF5555' },
    success: { main: '#2D8C3C' },
    error: { main: '#D32F2F' },
    background: { default: '#F5F5F5', paper: '#FFFFFF' },
    text: { primary: '#333333' },
  },
  typography: {
    fontFamily: '"Heebo", "Rubik", "Inter", system-ui, sans-serif',
  },
  shape: { borderRadius: 8 },
})
