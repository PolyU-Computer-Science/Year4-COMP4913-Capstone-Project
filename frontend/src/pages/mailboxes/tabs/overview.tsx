import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Hash, Plug, Tag, Text } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item'
import { Separator } from '@/components/ui/separator'
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

  const connectionState = mailbox.address && mailbox.imap_host ? 'Connected' : 'Not configured'
  const aiState = mailbox.classifier_config_id ? 'Configured' : 'Not configured'

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <section>
        <h3 className="mb-3 text-sm font-semibold">Mailbox health</h3>
        <div className="flex flex-col">
          <HealthRow label="Connection" value={connectionState} />
          <HealthRow
            label="Processing"
            value={mailbox.auto_process ? 'On' : 'Off'}
          />
          <HealthRow label="AI" value={aiState} />
        </div>
      </section>

      <Separator />

      <section>
        <h3 className="mb-3 text-sm font-semibold">Configuration</h3>
        <ItemGroup className="gap-1">
          <ConfigItem
            icon={<Tag />}
            title="Topics"
            description={
              topics.length > 0
                ? `${topics.length} topic${topics.length === 1 ? '' : 's'} configured`
                : 'No topics configured'
            }
            onClick={() => navigate(`/mailboxes/${mailbox.id}/data/topics`)}
          />
          <ConfigItem
            icon={<Text />}
            title="Custom fields"
            description={
              fields.length > 0
                ? `${fields.length} field${fields.length === 1 ? '' : 's'} configured`
                : 'No custom fields configured'
            }
            onClick={() => navigate(`/mailboxes/${mailbox.id}/data/fields`)}
          />
          <ConfigItem
            icon={<Hash />}
            title="Knowledge"
            description={
              knowledge.length > 0
                ? `${knowledge.length} source${knowledge.length === 1 ? '' : 's'} connected`
                : 'No knowledge sources connected'
            }
            onClick={() => navigate(`/mailboxes/${mailbox.id}/data/knowledge`)}
          />
          <ConfigItem
            icon={<Plug />}
            title="Connectors"
            description={
              enabledConnectors > 0
                ? `${enabledConnectors} connector${enabledConnectors === 1 ? '' : 's'} enabled`
                : 'No connectors enabled'
            }
            onClick={() => navigate(`/mailboxes/${mailbox.id}/integrations`)}
          />
        </ItemGroup>
      </section>
    </div>
  )
}

function HealthRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b py-3 text-sm last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

function ConfigItem({
  icon,
  title,
  description,
  onClick,
}: {
  icon: React.ReactNode
  title: string
  description: string
  onClick: () => void
}) {
  return (
    <Item
      variant="outline"
      className="cursor-pointer"
      onClick={onClick}
      render={<div />}
    >
      <ItemMedia variant="icon" className="size-8 rounded-lg bg-muted">
        {icon}
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{title}</ItemTitle>
        <ItemDescription>{description}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <ChevronRight className="size-4 text-muted-foreground" />
      </ItemActions>
    </Item>
  )
}
