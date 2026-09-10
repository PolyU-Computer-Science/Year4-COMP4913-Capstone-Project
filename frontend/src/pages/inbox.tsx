import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  Download,
  Inbox as InboxIcon,
  Loader2,
  Sparkles,
} from 'lucide-react'

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
import { fetchEmails, processAllEmails, processEmail, syncEmails } from '@/lib/api'
import type { EmailItem } from '@/lib/types'
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

export default function Inbox() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<EmailItem | null>(null)
  const [showImages, setShowImages] = useState(false)

  const [autoProcessing, setAutoProcessing] = useState(false)

  const { data: emails = [], isLoading } = useQuery({
    queryKey: ['emails'],
    queryFn: fetchEmails,
    refetchInterval: autoProcessing ? 2000 : false,
  })

  const syncMutation = useMutation({
    mutationFn: syncEmails,
    onSuccess: ({ synced }) => {
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      toast.success(
        synced > 0 ? `Fetched ${synced} new email${synced === 1 ? '' : 's'}` : 'Already up to date',
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
    mutationFn: processAllEmails,
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
        toast.success(
          `Processed ${processed} email${processed === 1 ? '' : 's'}`,
        )
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
    },
    onError: () => toast.error('Processing failed'),
  })

  const processingId = processMutation.isPending
    ? (processMutation.variables ?? null)
    : null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PageHeading
          title="Inbox"
          subtitle="Manage and process incoming emails"
        />
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            {emails.length} emails loaded
          </span>
          <Button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Download />
            )}
            Fetch Emails
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 py-12 text-muted-foreground">
          <Loader2 className="animate-spin" />
          <p className="text-sm">Loading emails…</p>
        </div>
      ) : emails.length === 0 ? (
        <div className="flex flex-col items-center gap-1 py-12 text-muted-foreground">
          <InboxIcon className="size-12" />
          <p className="text-lg">No emails loaded yet</p>
          <p className="text-sm">Click Fetch Emails to retrieve your inbox.</p>
        </div>
      ) : (
        <Card>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Subject</TableHead>
                  <TableHead>From</TableHead>
                  <TableHead>Received</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {emails.map((email) => {
                  const processing =
                    email.status === 'processing' || processingId === email.id
                  return (
                    <TableRow
                      key={email.id}
                      className="cursor-pointer"
                      onClick={() => {
                        setSelected(email)
                        setShowImages(false)
                      }}
                    >
                      <TableCell className="max-w-80 font-medium">
                        <span className="block truncate hover:underline">
                          {email.subject}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {email.sender}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(email.timestamp)}
                      </TableCell>
                      <TableCell>
                        {email.status === 'processing' || processing ? (
                          <Badge variant="outline" className="text-blue-600">
                            <Loader2 className="size-3 animate-spin" />
                            Processing
                          </Badge>
                        ) : email.status === 'processed' ? (
                          <Badge variant="secondary">
                            <CheckCircle2 className="size-3" />
                            Processed
                          </Badge>
                        ) : (
                          <span className="text-sm text-muted-foreground">
                            New
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
        <DialogContent className="sm:max-w-2xl">
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle>{selected.subject}</DialogTitle>
                <DialogDescription>
                  From: {selected.sender} · {formatDate(selected.timestamp)}
                </DialogDescription>
              </DialogHeader>
              <div className="max-h-[60vh] overflow-y-auto px-1">
                <EmailBody
                  body={selected.body}
                  html={selected.html}
                  emailId={selected.id}
                  showImages={showImages}
                />
              </div>
              <DialogFooter>
                {hasExternalImages(selected.html) && (
                  <Button
                    variant="outline"
                    className="mr-auto"
                    onClick={() => setShowImages((v) => !v)}
                  >
                    {showImages ? 'Hide images' : 'Display images'}
                  </Button>
                )}
                {selected.status === 'processing' || processingId === selected.id ? (
                  <Badge variant="outline" className="text-blue-600">
                    <Loader2 className="size-3 animate-spin" />
                    Processing
                  </Badge>
                ) : selected.status === 'processed' ? (
                  <>
                    <Badge variant="secondary" className="self-start">
                      <CheckCircle2 className="size-3" />
                      Processed
                    </Badge>
                    <Button
                      onClick={() => processMutation.mutate(selected.id)}
                      disabled={processingId !== null}
                    >
                      <Sparkles />
                      Re-process
                    </Button>
                  </>
                ) : (
                  <Button
                    onClick={() => processMutation.mutate(selected.id)}
                    disabled={processingId !== null}
                  >
                    <Sparkles />
                    AI Process
                  </Button>
                )}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
