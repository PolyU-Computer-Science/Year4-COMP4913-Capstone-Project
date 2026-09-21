import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Tag, Trash2 } from 'lucide-react'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { EmptyState } from '@/components/empty-state'
import { StatusBadge } from '@/components/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { createTopic, deleteTopic, fetchTopics } from '@/lib/api'
import type { Topic, TopicIn } from '@/lib/types'
import { toast } from 'sonner'

interface FormState {
  name: string
  description: string
  examples: string
}

const EMPTY: FormState = { name: '', description: '', examples: '' }

export function TopicsTab({ mailboxId }: { mailboxId: number }) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [toDelete, setToDelete] = useState<Topic | null>(null)

  const { data: topics = [] } = useQuery({
    queryKey: ['mailbox-topics', mailboxId],
    queryFn: () => fetchTopics(mailboxId),
  })

  const createMutation = useMutation({
    mutationFn: (payload: TopicIn) => createTopic(mailboxId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-topics', mailboxId] })
      setDialogOpen(false)
      setForm(EMPTY)
      toast.success('Topic added')
    },
    onError: () => toast.error('Failed to add topic'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTopic,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-topics', mailboxId] })
      toast.success('Topic deleted')
    },
    onError: () => toast.error('Failed to delete topic'),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Topics help the classifier understand the business context of this
          mailbox.
        </p>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus />
          Add Topic
        </Button>
      </div>

      {topics.length === 0 ? (
        <EmptyState
          icon={Tag}
          title="No topics yet"
          description="Define topics like Password Reset or Refund to guide classification."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus />
              Add Topic
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Topic</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {topics.map((topic) => (
                  <TableRow key={topic.id}>
                    <TableCell className="font-medium">{topic.name}</TableCell>
                    <TableCell className="max-w-96 truncate text-muted-foreground">
                      {topic.description || '—'}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={topic.status} />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setToDelete(topic)}
                      >
                        <Trash2 />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Topic</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Topic</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="Password Reset"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Description</Label>
              <Input
                value={form.description}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
                placeholder="Requests relating to forgotten passwords"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Examples</Label>
              <Textarea
                rows={3}
                value={form.examples}
                onChange={(e) =>
                  setForm((p) => ({ ...p, examples: e.target.value }))
                }
                placeholder={'One example per line:\nHow can I reset my password?'}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() =>
                createMutation.mutate({ ...form, status: 'active' })
              }
              disabled={createMutation.isPending || !form.name.trim()}
            >
              Add Topic
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => {
          if (!open) setToDelete(null)
        }}
        title={`Delete ${toDelete?.name ?? 'topic'}?`}
        description="Existing cases keep this topic. The classifier will no longer assign it to new emails."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (toDelete) deleteMutation.mutate(toDelete.id)
        }}
      />
    </div>
  )
}
