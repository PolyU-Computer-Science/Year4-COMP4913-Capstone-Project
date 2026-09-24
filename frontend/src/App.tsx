import { Navigate, Route, Routes } from 'react-router-dom'

import { AppHeader } from '@/components/app-header'
import { AppSidebar } from '@/components/app-sidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import CasesPage from '@/pages/cases'
import CaseDetailPage from '@/pages/case-detail'
import Dashboard from '@/pages/dashboard'
import Inbox from '@/pages/inbox'
import MailboxesPage from '@/pages/mailboxes'
import NewMailboxPage from '@/pages/mailboxes/new'
import MailboxDetailPage from '@/pages/mailboxes/detail'
import AIModelsPage from '@/pages/settings/ai-models'
import GeneralPage from '@/pages/settings/general'

function AppShell() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
            <Route path="/mailboxes" element={<MailboxesPage />} />
            <Route path="/mailboxes/new" element={<NewMailboxPage />} />
            <Route
              path="/mailboxes/:mailboxId/:section?"
              element={<MailboxDetailPage />}
            />
            <Route path="/settings/ai-models" element={<AIModelsPage />} />
            <Route path="/settings/general" element={<GeneralPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default function App() {
  return <AppShell />
}
