import { useQuery } from '@tanstack/react-query'
import { Loader2, MoreHorizontal } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { fetchMailbox } from '@/lib/api'
import { AiTab } from './tabs/ai'
import { ConnectionTab } from './tabs/connection'
import { ConnectorsTab } from './tabs/connectors'
import { DataTab } from './tabs/data'
import { ObservabilityTab } from './tabs/observability'
import { OverviewTab } from './tabs/overview'

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'connection', label: 'Connection' },
  { value: 'processing', label: 'Processing' },
  { value: 'data', label: 'Data' },
  { value: 'integrations', label: 'Integrations' },
  { value: 'activity', label: 'Activity' },
]

export default function MailboxDetailPage() {
  const { mailboxId, tab, sub } = useParams<{
    mailboxId: string
    tab?: string
    sub?: string
  }>()
  const navigate = useNavigate()
  const id = Number(mailboxId)

  // The `/data/:sub` route captures `sub` but no `tab`; map it back to `data`.
  const effectiveTab = tab ?? (sub ? 'data' : 'overview')

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

  const isSystem = mailbox.is_system
  const availableTabs = isSystem ? TABS.filter((t) => t.value === 'overview') : TABS
  const activeTab = availableTabs.some((t) => t.value === effectiveTab)
    ? effectiveTab
    : 'overview'

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={mailbox.name}
        description={mailbox.address || undefined}
        action={
          isSystem ? (
            <StatusBadge status="neutral" label="System" />
          ) : (
            <div className="flex items-center gap-2">
              <StatusBadge status={mailbox.status} />
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button variant="outline" size="icon-sm">
                      <MoreHorizontal />
                    </Button>
                  }
                />
                <DropdownMenuContent align="end" side="bottom">
                  <DropdownMenuItem onClick={() => navigate(`/mailboxes/${id}/connection`)}>
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive">
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )
        }
      />

      {mailbox.purpose ? (
        <p className="text-sm text-muted-foreground">{mailbox.purpose}</p>
      ) : null}

      {isSystem ? (
        <Alert>
          <AlertDescription>
            This is a system mailbox containing migrated emails whose original
            mailbox could not be identified. It cannot receive or send new
            mail.
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="overflow-x-auto">
        <Tabs
          value={activeTab}
          onValueChange={(value) => navigate(`/mailboxes/${id}/${value}`)}
        >
          <TabsList variant="line" className="w-fit">
            {availableTabs.map((t) => (
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
        {activeTab === 'processing' && <AiTab mailbox={mailbox} />}
        {activeTab === 'data' && <DataTab mailboxId={id} />}
        {activeTab === 'integrations' && <ConnectorsTab mailboxId={id} />}
        {activeTab === 'activity' && <ObservabilityTab mailboxId={id} />}
      </div>
    </div>
  )
}
