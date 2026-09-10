import { Routes, Route, useLocation } from 'react-router-dom'

import { AppSidebar } from '@/components/app-sidebar'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import Cases from '@/pages/cases'
import Dashboard from '@/pages/dashboard'
import Inbox from '@/pages/inbox'
import AISettingsPage from '@/pages/settings/ai'
import MailAccountsPage from '@/pages/settings/mail'

const TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/inbox': 'Inbox',
  '/cases': 'Cases',
  '/settings/ai': 'AI Settings',
  '/settings/mail': 'Mail Accounts',
}

function AppShell() {
  const location = useLocation()
  const title = TITLES[location.pathname] ?? 'Dashboard'

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <h1 className="text-lg font-semibold">{title}</h1>
          <div className="ml-auto flex items-center gap-2">
            <Badge variant="secondary">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              Online
            </Badge>
          </div>
        </header>
        <div className="flex flex-1 flex-col gap-4 p-4 md:p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/cases" element={<Cases />} />
            <Route path="/settings/ai" element={<AISettingsPage />} />
            <Route path="/settings/mail" element={<MailAccountsPage />} />
          </Routes>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default function App() {
  return <AppShell />
}
