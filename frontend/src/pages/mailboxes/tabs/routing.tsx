import { EmptyState } from '@/components/empty-state'
import { Route } from 'lucide-react'

export function RoutingTab({ mailboxId: _mailboxId }: { mailboxId: number }) {
  return (
    <EmptyState
      icon={Route}
      title="Routing not configured"
      description="Routing rules map classified emails to teams and agents. This will be available in a later sprint."
    />
  )
}
