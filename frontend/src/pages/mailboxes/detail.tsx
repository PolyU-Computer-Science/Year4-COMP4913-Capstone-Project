import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { fetchMailbox } from '@/lib/api'
import { AiTab } from './tabs/ai'
import { ConnectionTab } from './tabs/connection'
import { ConnectorsTab } from './tabs/connectors'
import { FieldsTab } from './tabs/fields'
import { KnowledgeTab } from './tabs/knowledge'
import { ObservabilityTab } from './tabs/observability'
import { OverviewTab } from './tabs/overview'
import { TopicsTab } from './tabs/topics'

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'connection', label: 'Connection' },
  { value: 'ai', label: 'AI & Processing' },
  { value: 'fields', label: 'Fields' },
  { value: 'topics', label: 'Topics' },
  { value: 'knowledge', label: 'Knowledge' },
  { value: 'connectors', label: 'Connectors' },
  { value: 'observability', label: 'Observability' },
]

export default function MailboxDetailPage() {
  const { mailboxId, tab = 'overview' } = useParams<{
    mailboxId: string
    tab?: string
  }>()
  const navigate = useNavigate()
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

  const activeTab = TABS.some((t) => t.value === tab) ? tab : 'overview'

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={mailbox.name}
        description={mailbox.address}
        action={<StatusBadge status={mailbox.status} />}
      />

      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">
          {mailbox.purpose || 'No description'}
        </p>
      </div>

      <div className="overflow-x-auto">
        <Tabs
          value={activeTab}
          onValueChange={(value) => navigate(`/mailboxes/${id}/${value}`)}
        >
          <TabsList variant="line" className="w-fit">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="pt-1">
        {activeTab === 'overview' && <OverviewTab mailbox={mailbox} />}
        {activeTab === 'connection' && <ConnectionTab mailbox={mailbox} />}
        {activeTab === 'ai' && <AiTab mailbox={mailbox} />}
        {activeTab === 'fields' && <FieldsTab mailboxId={id} />}
        {activeTab === 'topics' && <TopicsTab mailboxId={id} />}
        {activeTab === 'knowledge' && <KnowledgeTab mailboxId={id} />}
        {activeTab === 'connectors' && <ConnectorsTab mailboxId={id} />}
        {activeTab === 'observability' && <ObservabilityTab mailboxId={id} />}
      </div>
    </div>
  )
}
