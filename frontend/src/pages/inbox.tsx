import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Download,
  Inbox as InboxIcon,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react'

import { EmailBody } from '@/components/email-body'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  fetchEmails,
  fetchMailboxes,
  processAllEmails,
  processEmail,
  syncEmails,
} from '@/lib/api'
import type { EmailItem } from '@/lib/types'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function hasExternalImages(html: string): boolean {
  return /<img[^>]+src=["']https?:\/\//i.test(html)
}

export default function Inbox() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<EmailItem | null>(null)
  const [showImages, setShowImages] = useState(false)
  const [query, setQuery] = useState('')
  const [mailboxFilter, setMailboxFilter] = useState<string>('all')
  const [autoProcessing, setAutoProcessing] = useState(false)

  const activeMailboxId = mailboxFilter === 'all' ? undefined : Number(mailboxFilter)

  const { data: emails = [], isLoading } = useQuery({
    queryKey: ['emails', activeMailboxId],
    queryFn: () => fetchEmails(activeMailboxId),
    refetchInterval: autoProcessing ? 2000 : false,
  })
  const { data: mailboxes = [] } = useQuery({
    queryKey: ['mailboxes'],
    queryFn: fetchMailboxes,
  })

  const syncMutation = useMutation({
    mutationFn: () => syncEmails(activeMailboxId),
    onSuccess: ({ synced }) => {
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      toast.success(
        synced > 0
          ? `Fetched ${synced} new email${synced === 1 ? '' : 's'}`
          : 'Already up to date',
      )
      setAutoProcessing(true)
      processAllMutation.mutate()
    },
    onError: (error) => {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail ?? 'Fetch failed')
    },
  })

  const processAllMutation = useMutation({
    mutationFn: () => processAllEmails(activeMailboxId),
    onSuccess: ({ processed, failed }) => {
      setAutoProcessing(false)
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      if (failed.length > 0) {
        toast.warning(
          `Processed ${processed} email${processed === 1 ? '' : 's'}, ${failed.length} failed`,
        )
      } else if (processed > 0) {
        toast.success(`Processed ${processed} email${processed === 1 ? '' : 's'}`)
      }
    },
    onError: (error) => {
      setAutoProcessing(false)
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail ?? 'Auto-processing failed')
    },
  })

  const processMutation = useMutation({
    mutationFn: processEmail,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      toast.success('Email processed!')
      setSelected(null)
    },
    onError: () => toast.error('Processing failed'),
  })

  const filtered = emails.filter((email) => {
    if (query && !`${email.subject} ${email.sender}`.toLowerCase().includes(query.toLowerCase())) {
      return false
    }
    return true
  })

  const processingId = processMutation.isPending
    ? (processMutation.variables ?? null)
    : null

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Inbox"
        description="Read and process incoming emails."
        action={
          <Button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Download />
            )}
            Sync Mail
          </Button>
        }
      />

      {isLoading ? (
        <div className="flex items-center gap-2 py-12 text-muted-foreground">
          <Loader2 className="animate-spin" />
          <p className="text-sm">Loading emails…</p>
        </div>
      ) : emails.length === 0 ? (
        <EmptyState
          icon={InboxIcon}
          title="No emails yet"
          description="Sync your mailbox to start receiving and processing emails."
          action={
            <Button onClick={() => syncMutation.mutate()}>Sync Mail</Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <div className="flex flex-col gap-3">
            <div className="relative">
              <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-8"
                placeholder="Search email…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <Select value={mailboxFilter} onValueChange={(v) => setMailboxFilter(v ?? 'all')}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All Mailboxes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Mailboxes</SelectItem>
                {mailboxes.map((mailbox) => (
                  <SelectItem key={mailbox.id} value={String(mailbox.id)}>
                    {mailbox.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex flex-col gap-1 overflow-y-auto">
              {filtered.map((email) => (
                <button
                  key={email.id}
                  onClick={() => {
                    setSelected(email)
                    setShowImages(false)
                  }}
                  className={cn(
                    'flex flex-col gap-1 rounded-lg border p-3 text-left transition-colors hover:bg-muted/50',
                    selected?.id === email.id && 'border-ring bg-muted/50',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">
                      {email.subject}
                    </span>
                    {email.status === 'new' ? (
                      <span className="size-2 shrink-0 rounded-full bg-primary" />
                    ) : null}
                  </div>
                  <span className="truncate text-xs text-muted-foreground">
                    {email.sender}
                  </span>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {formatDate(email.timestamp)}
                    </span>
                    <StatusBadge status={email.status} />
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-xl border">
            {selected === null ? (
              <div className="flex h-full min-h-64 items-center justify-center text-sm text-muted-foreground">
                Select an email to read it.
              </div>
            ) : (
              <div className="flex flex-col gap-4 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <h2 className="text-lg font-semibold">{selected.subject}</h2>
                    <span className="text-sm text-muted-foreground">
                      From: {selected.sender} · {formatDate(selected.timestamp)}
                    </span>
                  </div>
                  <StatusBadge status={selected.status} />
                </div>

                <div className="max-h-[60vh] overflow-y-auto">
                  <EmailBody
                    body={selected.body}
                    html={selected.html}
                    emailId={selected.id}
                    showImages={showImages}
                  />
                </div>

                <div className="flex items-center gap-2 border-t pt-3">
                  {hasExternalImages(selected.html) && (
                    <Button
                      variant="outline"
                      onClick={() => setShowImages((v) => !v)}
                    >
                      {showImages ? 'Hide images' : 'Display images'}
                    </Button>
                  )}
                  <div className="ml-auto flex items-center gap-2">
                    {selected.status === 'processing' ||
                    processingId === selected.id ? (
                      <Badge variant="outline" className="text-blue-600">
                        <Loader2 className="size-3 animate-spin" />
                        Processing
                      </Badge>
                    ) : (
                      <Button
                        onClick={() => processMutation.mutate(selected.id)}
                        disabled={processingId !== null}
                      >
                        <Sparkles />
                        Process with AI
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
