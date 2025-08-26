import { ReactNode } from 'react'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background text-text" dir="rtl">
      {children}
    </div>
  )
}
