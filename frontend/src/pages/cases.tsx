import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FolderOpen, Loader2, Send } from 'lucide-react'

import { CategoryBadge } from '@/components/category-badge'
import { EmailBody } from '@/components/email-body'
import { PageHeading } from '@/components/page-heading'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { fetchCases, sendCase, updateCaseDraft } from '@/lib/api'
import type { Case } from '@/lib/types'
import { toast } from 'sonner'

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function hasExternalImages(html: string): boolean {
  return /<img[^>]+src=["']https?:\/\//i.test(html)
}

export default function Cases() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Case | null>(null)
  const [showImages, setShowImages] = useState(false)
  const [draft, setDraft] = useState('')

  const { data: cases = [] } = useQuery<Case[]>({
    queryKey: ['cases'],
    queryFn: fetchCases,
  })

  const saveDraftMutation = useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: string }) =>
      updateCaseDraft(id, draft),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      setSelected(updated)
      setDraft(updated.draft)
      toast.success('Draft saved')
    },
    onError: () => toast.error('Failed to save draft'),
  })

  const sendMutation = useMutation({
    mutationFn: sendCase,
    onSuccess: (sent) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      setSelected(sent)
      toast.success('Reply sent!')
    },
    onError: (error) => {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail ?? 'Failed to send')
    },
  })

  function openCase(item: Case) {
    setSelected(item)
    setDraft(item.draft)
    setShowImages(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeading
        title="Cases"
        subtitle="Processed emails and AI-generated draft replies"
      />

      {cases.length === 0 ? (
        <div className="flex flex-col items-center gap-1 py-12 text-muted-foreground">
          <FolderOpen className="size-12" />
          <p className="text-lg">No processed cases yet</p>
          <p className="text-sm">
            Go to Inbox and click AI Process on an email.
          </p>
        </div>
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subject</TableHead>
                  <TableHead>From</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Processed</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cases.map((item) => {
                  const sent = item.sent_at !== null
                  return (
                    <TableRow
                      key={item.id}
                      className="cursor-pointer"
                      onClick={() => openCase(item)}
                    >
                      <TableCell className="max-w-72 font-medium">
                        <span className="block truncate hover:underline">
                          {item.email.subject}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {item.email.sender}
                      </TableCell>
                      <TableCell>
                        <CategoryBadge
                          category={item.classification.category}
                        />
                      </TableCell>
                      <TableCell>{item.classification.priority}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(item.created_at)}
                      </TableCell>
                      <TableCell>
                        {sent ? (
                          <Badge
                            variant="secondary"
                            className="border-transparent bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                          >
                            <CheckCircle2 className="size-3" />
                            Sent
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            Draft
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelected(null)
            setShowImages(false)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle>{selected.email.subject}</DialogTitle>
                <DialogDescription>
                  From: {selected.email.sender} ·{' '}
                  {formatDate(selected.email.timestamp)}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <span className="text-sm font-semibold">Email</span>
                  <div className="max-h-48 overflow-y-auto rounded-lg border bg-muted/30 p-3">
                    <EmailBody
                      body={selected.email.body}
                      html={selected.email.html}
                      emailId={selected.email.id}
                      showImages={showImages}
                    />
                    {hasExternalImages(selected.email.html) && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-2"
                        onClick={() => setShowImages((v) => !v)}
                      >
                        {showImages ? 'Hide images' : 'Display images'}
                      </Button>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <span className="text-sm font-semibold">Classification</span>
                  <div className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <CategoryBadge
                        category={selected.classification.category}
                      />
                      {selected.classification.topic && (
                        <Badge variant="outline">
                          {selected.classification.topic}
                        </Badge>
                      )}
                      <Badge variant="outline">
                        {selected.classification.priority}
                      </Badge>
                      <Badge variant="outline">
                        urgency {selected.classification.urgency_score}/10
                      </Badge>
                    </div>
                    {selected.classification.summary && (
                      <p className="text-muted-foreground">
                        {selected.classification.summary}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <span className="text-sm font-semibold">AI Draft Reply</span>
                  <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
                    <span className="text-sm text-muted-foreground">Subject</span>
                    <span className="truncate text-sm">
                      Re: {selected.email.subject}
                    </span>
                  </div>
                  <Textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    rows={8}
                    className="w-full"
                    disabled={selected.sent_at !== null}
                  />
                </div>
              </div>

              <DialogFooter>
                {selected.sent_at !== null ? (
                  <Badge
                    variant="secondary"
                    className="border-transparent bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                  >
                    <CheckCircle2 className="size-3" />
                    Sent {formatDate(selected.sent_at)}
                  </Badge>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={() =>
                        saveDraftMutation.mutate({ id: selected.id, draft })
                      }
                      disabled={saveDraftMutation.isPending}
                    >
                      {saveDraftMutation.isPending ? (
                        <Loader2 className="animate-spin" />
                      ) : null}
                      Save Draft
                    </Button>
                    <Button
                      onClick={() => sendMutation.mutate(selected.id)}
                      disabled={
                        sendMutation.isPending || draft.trim().length === 0
                      }
                    >
                      {sendMutation.isPending ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <Send />
                      )}
                      Send
                    </Button>
                  </>
                )}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
