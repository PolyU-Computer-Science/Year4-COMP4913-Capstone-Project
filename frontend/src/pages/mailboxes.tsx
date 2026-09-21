import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Mailbox as MailboxIcon, MoreHorizontal, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
        description="Manage business email contexts and their AI configuration."
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
          <Card>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Purpose</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>AI</TableHead>
                    <TableHead className="w-8" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((mailbox) => (
                    <TableRow
                      key={mailbox.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/mailboxes/${mailbox.id}/overview`)}
                    >
                      <TableCell className="font-medium">{mailbox.name}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {mailbox.address}
                      </TableCell>
                      <TableCell className="max-w-52 truncate text-muted-foreground">
                        {mailbox.purpose || '—'}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={mailbox.status} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge
                          status={mailbox.classifier_config_id ? 'ready' : 'warning'}
                          label={mailbox.classifier_config_id ? 'Ready' : 'Unconfigured'}
                        />
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            render={
                              <Button variant="ghost" size="icon-sm">
                                <MoreHorizontal />
                              </Button>
                            }
                          />
                          <DropdownMenuContent align="end" side="bottom">
                            <DropdownMenuItem
                              onClick={() =>
                                navigate(`/mailboxes/${mailbox.id}/overview`)
                              }
                            >
                              Open
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                navigate(`/mailboxes/${mailbox.id}/connection`)
                              }
                            >
                              Connection
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setToDelete(mailbox)}
                            >
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
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
