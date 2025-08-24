import { RouteObject } from 'react-router-dom'
import LoginPage from './pages/login'
import MessagesPage from './pages/messages'

const routes: RouteObject[] = [
  { path: '/', element: <LoginPage /> },
  { path: '/messages', element: <MessagesPage /> },
]

export default routes
