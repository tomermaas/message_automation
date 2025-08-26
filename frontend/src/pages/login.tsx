import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStatus } from '../hooks/useStatus'
import { api } from '../lib/api'
import toast from 'react-hot-toast'
import { Avatar } from '@mui/material'

export default function LoginPage() {
  const nav = useNavigate()
  const status = useStatus()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  useEffect(() => {
    if (status.data?.logged_in) nav('/messages')
  }, [status.data, nav])

  async function submit(e: FormEvent) {
    e.preventDefault()
    try {
      await api.login(username, password)
      nav('/messages')
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-background">
      <button onClick={() => window.close()} className="fixed top-4 right-4 bg-gray-300 px-2 py-1 rounded focus-visible:outline-primary focus-visible:outline-2">
        יציאה
      </button>
      <form onSubmit={submit} className="bg-white p-6 rounded shadow w-80 flex flex-col gap-3">
        <div className="flex flex-col items-center gap-2 mb-2">
          <Avatar />
          <h1 className="text-xl font-bold">כניסה</h1>
        </div>
        <input
          className="border p-2 rounded focus-visible:outline-primary focus-visible:outline-2"
          placeholder="משתמש"
          value={username}
          onChange={e => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="border p-2 rounded focus-visible:outline-primary focus-visible:outline-2"
          placeholder="סיסמה"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <a href="#" className="text-sm text-primary text-left">שכחת סיסמה?</a>
        <button className="mt-2 bg-primary text-white py-2 rounded hover:brightness-110 transition focus-visible:outline-primary focus-visible:outline-2" type="submit">
          כניסה
        </button>
      </form>
    </div>
  )
}
