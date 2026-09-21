import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { StatusBadge } from '@/components/status-badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  fetchMailboxConnectors,
  fetchMailboxKnowledge,
  fetchTopics,
  fetchCustomFields,
} from '@/lib/api'
import type { Mailbox } from '@/lib/types'

export function OverviewTab({ mailbox }: { mailbox: Mailbox }) {
  const navigate = useNavigate()

  const { data: topics = [] } = useQuery({
    queryKey: ['mailbox-topics', mailbox.id],
    queryFn: () => fetchTopics(mailbox.id),
  })
  const { data: fields = [] } = useQuery({
    queryKey: ['mailbox-fields', mailbox.id],
    queryFn: () => fetchCustomFields(mailbox.id),
  })
  const { data: knowledge = [] } = useQuery({
    queryKey: ['mailbox-knowledge', mailbox.id],
    queryFn: () => fetchMailboxKnowledge(mailbox.id),
  })
  const { data: connectors = [] } = useQuery({
    queryKey: ['mailbox-connectors', mailbox.id],
    queryFn: () => fetchMailboxConnectors(mailbox.id),
  })

  const enabledConnectors = connectors.filter((c) => c.enabled).length

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatusCard label="Incoming Mail" status="Healthy" />
        <StatusCard label="Outgoing Mail" status="Healthy" />
        <StatusCard
          label="AI"
          status={mailbox.classifier_config_id ? 'Ready' : 'Error'}
        />
        <StatusCard
          label="Knowledge"
          status={knowledge.length > 0 ? 'Ready' : 'Disabled'}
        />
        <StatusCard
          label="Connectors"
          status={enabledConnectors > 0 ? 'Connected' : 'Disabled'}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
            <CardDescription>
              What is configured on this mailbox.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <ConfigRow
              label="Topics"
              value={`${topics.length}`}
              onClick={() => navigate(`/mailboxes/${mailbox.id}/topics`)}
            />
            <ConfigRow
              label="Custom Fields"
              value={`${fields.length}`}
              onClick={() => navigate(`/mailboxes/${mailbox.id}/fields`)}
            />
            <ConfigRow
              label="Knowledge"
              value={`${knowledge.length} source${knowledge.length === 1 ? '' : 's'}`}
              onClick={() => navigate(`/mailboxes/${mailbox.id}/knowledge`)}
            />
            <ConfigRow
              label="Connectors"
              value={`${enabledConnectors} enabled`}
              onClick={() => navigate(`/mailboxes/${mailbox.id}/connectors`)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Processing</CardTitle>
            <CardDescription>How incoming mail is handled.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Auto-process incoming mail</span>
              <StatusBadge
                status={mailbox.auto_process ? 'active' : 'disabled'}
                label={mailbox.auto_process ? 'On' : 'Off'}
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Generate reply drafts</span>
              <StatusBadge
                status={mailbox.generate_drafts ? 'active' : 'disabled'}
                label={mailbox.generate_drafts ? 'On' : 'Off'}
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Human approval</span>
              <StatusBadge status="active" label="Required" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function StatusCard({ label, status }: { label: string; status: string }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border p-3">
      <span className="text-xs text-muted-foreground">{label}</span>
      <StatusBadge status={status} />
    </div>
  )
}

function ConfigRow({
  label,
  value,
  onClick,
}: {
  label: string
  value: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors hover:bg-muted/50"
    >
      <span>{label}</span>
      <span className="font-medium">{value}</span>
    </button>
  )
}
