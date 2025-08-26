import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStatus } from '../hooks/useStatus'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

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
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <button onClick={() => window.close()} className="fixed top-4 right-4 bg-gray-300 px-2 py-1 rounded">
        יציאה
      </button>
      <form onSubmit={submit} className="bg-white p-6 rounded shadow w-80 flex flex-col gap-2">
        <h1 className="text-xl mb-2 text-center">כניסה</h1>
        <input className="border p-2" placeholder="משתמש" value={username} onChange={e => setUsername(e.target.value)} />
        <input type="password" className="border p-2" placeholder="סיסמה" value={password} onChange={e => setPassword(e.target.value)} />
        <button className="mt-2 bg-blue-600 text-white py-1 rounded" type="submit">כניסה</button>
      </form>
    </div>
  )
}
