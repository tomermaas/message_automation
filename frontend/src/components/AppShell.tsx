import { ReactNode } from 'react'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen" dir="rtl">
      {children}
    </div>
  )
}
