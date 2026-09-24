import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useParams } from 'react-router-dom'

import { PageHeader } from '@/components/page-header'
import { fetchMailbox } from '@/lib/api'
import { MailboxLocalNav, resolveSection } from './mailbox-local-nav'
import { MAILBOX_SECTION_MAP } from './sections'
import { AiTab } from './tabs/ai'
import { ConnectionTab } from './tabs/connection'
import { ConnectorsTab } from './tabs/connectors'
import { FieldsTab } from './tabs/fields'
import { KnowledgeTab } from './tabs/knowledge'
import { ObservabilityTab } from './tabs/observability'
import { OverviewTab } from './tabs/overview'
import { RoutingTab } from './tabs/routing'
import { TopicsTab } from './tabs/topics'

export default function MailboxDetailPage() {
  const { mailboxId, section } = useParams<{
    mailboxId: string
    section?: string
  }>()
  const id = Number(mailboxId)

  const { data: mailbox, isLoading } = useQuery({
    queryKey: ['mailbox', id],
    queryFn: () => fetchMailbox(id),
    enabled: !Number.isNaN(id),
  })

  if (isLoading || !mailbox) {
    return (
      <div className="flex items-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="animate-spin" />
        <p className="text-sm">Loading mailbox…</p>
      </div>
    )
  }

  const active = resolveSection(section ?? 'overview')
  const activeSection = MAILBOX_SECTION_MAP[active]

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1">
        <MailboxLocalNav mailbox={mailbox} active={active} />

        <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
          <div className="flex flex-col gap-4 p-4 md:p-6">
            <PageHeader
              title={activeSection.label}
              description={activeSection.description}
            />

            {active === 'overview' && <OverviewTab mailbox={mailbox} />}
            {active === 'connection' && <ConnectionTab mailbox={mailbox} />}
            {active === 'processing' && <AiTab mailbox={mailbox} />}
            {active === 'topics' && <TopicsTab mailboxId={id} />}
            {active === 'fields' && <FieldsTab mailboxId={id} />}
            {active === 'knowledge' && <KnowledgeTab mailboxId={id} />}
            {active === 'routing' && <RoutingTab mailboxId={id} />}
            {active === 'connectors' && <ConnectorsTab mailboxId={id} />}
            {active === 'activity' && <ObservabilityTab mailboxId={id} />}
          </div>
        </main>
      </div>
    </div>
  )
}
