import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Loader2, Plus, Search, Trash2 } from 'lucide-react'

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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  assignKnowledge,
  createKnowledgeSource,
  fetchKnowledgeSources,
  fetchMailboxKnowledge,
  indexKnowledgeSource,
  searchKnowledge,
  unassignKnowledge,
} from '@/lib/api'
import type { KnowledgeSource, RetrievalResponse } from '@/lib/types'
import { toast } from 'sonner'

export function KnowledgeTab({ mailboxId }: { mailboxId: number }) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('document')
  const [newContent, setNewContent] = useState('')
  const [toRemove, setToRemove] = useState<KnowledgeSource | null>(null)
  const [retrievalOpen, setRetrievalOpen] = useState(false)

  const { data: assigned = [] } = useQuery({
    queryKey: ['mailbox-knowledge', mailboxId],
    queryFn: () => fetchMailboxKnowledge(mailboxId),
  })
  const { data: allSources = [] } = useQuery({
    queryKey: ['knowledge-sources'],
    queryFn: fetchKnowledgeSources,
  })

  const assignedIds = new Set(assigned.map((s) => s.id))
  const unassigned = allSources.filter((s) => !assignedIds.has(s.id))

  const createMutation = useMutation({
    mutationFn: createKnowledgeSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-sources'] })
      setNewName('')
      setNewContent('')
      setDialogOpen(false)
      toast.success('Knowledge source created')
    },
    onError: () => toast.error('Failed to create knowledge source'),
  })

  const assignMutation = useMutation({
    mutationFn: (sourceId: number) => assignKnowledge(mailboxId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-knowledge', mailboxId] })
      toast.success('Knowledge assigned')
    },
    onError: () => toast.error('Failed to assign knowledge'),
  })

  const unassignMutation = useMutation({
    mutationFn: (sourceId: number) => unassignKnowledge(mailboxId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-knowledge', mailboxId] })
      toast.success('Knowledge removed')
    },
    onError: () => toast.error('Failed to remove knowledge'),
  })

  const indexMutation = useMutation({
    mutationFn: (sourceId: number) => indexKnowledgeSource(mailboxId, sourceId),
    onSuccess: (result) => {
      if (result.status === 'indexed') {
        queryClient.invalidateQueries({ queryKey: ['mailbox-knowledge', mailboxId] })
        toast.success(
          result.skipped ? 'Already up to date' : `Indexed ${result.chunks} chunks`,
        )
      } else {
        toast.error(result.error ?? 'Indexing failed')
      }
    },
    onError: () => toast.error('Indexing failed'),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Knowledge available to this mailbox.
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setRetrievalOpen(true)} disabled={assigned.length === 0}>
            Test Retrieval
          </Button>
          <Button onClick={() => setDialogOpen(true)}>
            <Plus />
            Add Source
          </Button>
        </div>
      </div>

      {assigned.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No knowledge sources"
          description="Add FAQs, documentation, or policy files to ground AI-generated replies."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus />
              Add Source
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead className="w-28 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assigned.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell className="font-medium">{source.name}</TableCell>
                    <TableCell className="capitalize">{source.type}</TableCell>
                    <TableCell>
                      <StatusBadge status={source.status} />
                    </TableCell>
                    <TableCell>{source.chunks}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => indexMutation.mutate(source.id)}
                          disabled={indexMutation.isPending}
                        >
                          {indexMutation.isPending ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            'Index'
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setToRemove(source)}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Knowledge Source</DialogTitle>
          </DialogHeader>

          {unassigned.length > 0 && (
            <div className="flex flex-col gap-2">
              <Label>Select existing</Label>
              <div className="relative">
                <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border p-2">
                  {unassigned.map((source) => (
                    <button
                      key={source.id}
                      onClick={() => assignMutation.mutate(source.id)}
                      className="flex items-center justify-between rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted/50"
                    >
                      <span>{source.name}</span>
                      <span className="text-xs text-muted-foreground capitalize">
                        {source.type}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-2 border-t pt-3">
            <Label>Create new</Label>
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Support FAQ"
            />
            <Select value={newType} onValueChange={(v) => setNewType(v ?? 'document')}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="document">Document</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="website">Website</SelectItem>
              </SelectContent>
            </Select>
            <Label>Content</Label>
            <Textarea
              rows={5}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Paste the knowledge content to index…"
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() =>
                createMutation.mutate({
                  name: newName,
                  type: newType,
                  status: 'ready',
                  chunks: 0,
                  content: newContent,
                })
              }
              disabled={createMutation.isPending || !newName.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <RetrievalSheet
        mailboxId={mailboxId}
        open={retrievalOpen}
        onOpenChange={setRetrievalOpen}
      />

      <ConfirmDialog
        open={toRemove !== null}
        onOpenChange={(open) => {
          if (!open) setToRemove(null)
        }}
        title={`Remove ${toRemove?.name ?? 'source'}?`}
        description="This mailbox will no longer use this knowledge source."
        confirmLabel="Remove"
        destructive
        onConfirm={() => {
          if (toRemove) unassignMutation.mutate(toRemove.id)
        }}
      />
    </div>
  )
}

function RetrievalSheet({
  mailboxId,
  open,
  onOpenChange,
}: {
  mailboxId: number
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState('5')
  const [data, setData] = useState<RetrievalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const searchMutation = useMutation({
    mutationFn: () => searchKnowledge(mailboxId, query, Number(topK)),
    onSuccess: (result) => {
      setData(result)
      setError(null)
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail ?? 'Embedding service unavailable')
    },
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Retrieval Test</SheetTitle>
          <SheetDescription>
            Test mailbox-scoped knowledge retrieval.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Query</Label>
            <Textarea
              rows={2}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What is the refund period?"
            />
          </div>
          <div className="flex items-center gap-2">
            <div className="flex flex-col gap-1.5">
              <Label>Top K</Label>
              <Input
                className="w-20"
                type="number"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
              />
            </div>
            <Button
              className="mt-auto"
              onClick={() => searchMutation.mutate()}
              disabled={searchMutation.isPending || !query.trim()}
            >
              {searchMutation.isPending ? <Loader2 className="animate-spin" /> : 'Run'}
            </Button>
          </div>

          {error !== null && (
            <div className="flex flex-col gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
              <p className="text-sm font-medium text-destructive">Retrieval failed</p>
              <p className="text-xs text-muted-foreground">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="self-start"
                onClick={() => searchMutation.mutate()}
              >
                Try Again
              </Button>
            </div>
          )}

          {data !== null && error === null && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>
                  {data.stats.returned_count} result{data.stats.returned_count === 1 ? '' : 's'}
                  {' · '}
                  {data.stats.latency_ms.toFixed(0)} ms
                </span>
                <span>
                  {data.embedding.model}
                  {data.embedding.dim > 0 ? ` · ${data.embedding.dim} dims` : ''}
                </span>
              </div>

              {data.results.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </p>
              ) : (
                data.results.map((result, index) => (
                  <div key={result.chunk_id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">
                        #{index + 1} {result.source_name}
                      </span>
                      <span className="text-xs font-medium text-muted-foreground">
                        {result.score.toFixed(3)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">
                      {result.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
