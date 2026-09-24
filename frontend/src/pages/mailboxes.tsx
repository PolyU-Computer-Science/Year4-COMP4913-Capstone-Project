import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Mailbox as MailboxIcon, MoreHorizontal, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { deleteMailbox, fetchMailboxes } from '@/lib/api'
import type { Mailbox } from '@/lib/types'
import { toast } from 'sonner'

export default function MailboxesPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [toDelete, setToDelete] = useState<Mailbox | null>(null)

  const { data: mailboxes = [] } = useQuery({
    queryKey: ['mailboxes'],
    queryFn: fetchMailboxes,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteMailbox,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailboxes'] })
      toast.success('Mailbox deleted')
    },
    onError: () => toast.error('Failed to delete mailbox'),
  })

  const filtered = mailboxes.filter((mailbox) => {
    if (!query) return true
    return `${mailbox.name} ${mailbox.address} ${mailbox.purpose}`
      .toLowerCase()
      .includes(query.toLowerCase())
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Mailboxes"
        description="Manage email sources and processing."
        action={
          <Button onClick={() => navigate('/mailboxes/new')}>
            <Plus />
            Add Mailbox
          </Button>
        }
      />

      {mailboxes.length === 0 ? (
        <EmptyState
          icon={MailboxIcon}
          title="No mailboxes yet"
          description="Connect your first business mailbox to start receiving and processing emails."
          action={
            <Button onClick={() => navigate('/mailboxes/new')}>
              <Plus />
              Add Mailbox
            </Button>
          }
        />
      ) : (
        <>
          <Input
            className="w-72"
            placeholder="Search mailboxes…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((mailbox) => (
              <MailboxCard
                key={mailbox.id}
                mailbox={mailbox}
                onOpen={() => navigate(`/mailboxes/${mailbox.id}/overview`)}
                onDelete={() => setToDelete(mailbox)}
              />
            ))}
          </div>
        </>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => {
          if (!open) setToDelete(null)
        }}
        title={`Delete ${toDelete?.name ?? 'mailbox'}?`}
        description="This will permanently remove the mailbox and its configuration."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (toDelete) deleteMutation.mutate(toDelete.id)
        }}
      />
    </div>
  )
}

function MailboxCard({
  mailbox,
  onOpen,
  onDelete,
}: {
  mailbox: Mailbox
  onOpen: () => void
  onDelete: () => void
}) {
  return (
    <div
      className="group flex cursor-pointer flex-col gap-2 rounded-xl border p-4 transition-colors hover:border-ring"
      onClick={onOpen}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate font-medium">{mailbox.name}</span>
        <StatusBadge status={mailbox.status} />
      </div>
      {mailbox.address ? (
        <span className="truncate text-sm text-muted-foreground">
          {mailbox.address}
        </span>
      ) : null}
      {mailbox.purpose ? (
        <span className="line-clamp-2 text-sm text-muted-foreground">
          {mailbox.purpose}
        </span>
      ) : null}
      <div className="mt-auto flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {mailbox.classifier_config_id ? 'AI configured' : 'AI not configured'}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button variant="ghost" size="icon-sm" className="opacity-0 group-hover:opacity-100">
                <MoreHorizontal />
              </Button>
            }
          />
          <DropdownMenuContent align="end" side="bottom">
            <DropdownMenuItem onClick={onOpen}>Open</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-destructive" onClick={onDelete}>
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
