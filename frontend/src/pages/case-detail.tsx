import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Send } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { CategoryBadge } from '@/components/category-badge'
import { CaseFields } from '@/components/case-fields'
import { EmailBody } from '@/components/email-body'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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

export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState('')

  const { data: cases = [] } = useQuery<Case[]>({
    queryKey: ['cases'],
    queryFn: () => fetchCases(),
  })

  const caseItem = cases.find((item) => item.id === caseId)

  useEffect(() => {
    if (caseItem) setDraft(caseItem.draft)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId])

  const saveDraftMutation = useMutation({
    mutationFn: ({ id, draft }: { id: string; draft: string }) =>
      updateCaseDraft(id, draft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      toast.success('Draft saved')
    },
    onError: () => toast.error('Failed to save draft'),
  })

  const sendMutation = useMutation({
    mutationFn: sendCase,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['emails'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
      toast.success('Reply sent!')
    },
    onError: (error) => {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail ?? 'Failed to send')
    },
  })

  if (!caseItem) {
    return (
      <div className="flex items-center gap-2 py-12 text-muted-foreground">
        <Loader2 className="animate-spin" />
        <p className="text-sm">Loading case…</p>
      </div>
    )
  }

  const sent = caseItem.sent_at !== null

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={`#${caseItem.id.slice(0, 6).toUpperCase()}`}
        description={caseItem.email.subject}
        action={
          <div className="flex items-center gap-2">
            <StatusBadge status={sent ? 'sent' : 'draft'} />
            <Badge
              variant="outline"
              className="capitalize"
            >
              {caseItem.classification.priority}
            </Badge>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Original Message</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div className="text-sm">
                <span className="font-medium">{caseItem.email.sender}</span>
              </div>
              <div className="max-h-72 overflow-y-auto rounded-lg border bg-muted/30 p-3">
                <EmailBody
                  body={caseItem.email.body}
                  html={caseItem.email.html}
                  emailId={caseItem.email.id}
                />
              </div>
              <span className="text-xs text-muted-foreground">
                {formatDate(caseItem.email.timestamp)}
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Analysis</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 text-sm">
              <div className="flex items-center gap-2">
                <CategoryBadge category={caseItem.classification.category} />
                {caseItem.classification.topic && (
                  <Badge variant="outline">{caseItem.classification.topic}</Badge>
                )}
                {caseItem.topic_id === null && caseItem.topic_raw && (
                  <Badge variant="outline" className="text-muted-foreground">
                    Unclassified
                  </Badge>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-muted-foreground">Priority</span>
                  <span className="capitalize">{caseItem.classification.priority}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-muted-foreground">Urgency</span>
                  <span>{caseItem.classification.urgency_score}/10</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs text-muted-foreground">Requires Reply</span>
                  <span>{caseItem.classification.summary ? 'Yes' : 'No'}</span>
                </div>
              </div>
              {caseItem.classification.summary && (
                <p className="text-muted-foreground">
                  {caseItem.classification.summary}
                </p>
              )}
            </CardContent>
          </Card>

          <CaseFields caseId={caseItem.id} />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>AI Draft</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
              <span className="text-sm text-muted-foreground">To</span>
              <span className="truncate text-sm">{caseItem.email.sender}</span>
            </div>
            <div className="flex items-center gap-2 rounded-lg border bg-muted/30 px-3 py-2">
              <span className="text-sm text-muted-foreground">Subject</span>
              <span className="truncate text-sm">Re: {caseItem.email.subject}</span>
            </div>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={12}
              className="w-full"
              disabled={sent}
            />
          </CardContent>
          <div className="flex items-center justify-end gap-2 border-t p-4">
            {sent ? (
              <StatusBadge status="sent" label={`Sent ${formatDate(caseItem.sent_at!)}`} />
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() =>
                    saveDraftMutation.mutate({ id: caseItem.id, draft })
                  }
                  disabled={saveDraftMutation.isPending}
                >
                  {saveDraftMutation.isPending ? (
                    <Loader2 className="animate-spin" />
                  ) : null}
                  Save Draft
                </Button>
                <Button
                  onClick={() => sendMutation.mutate(caseItem.id)}
                  disabled={sendMutation.isPending || draft.trim().length === 0}
                >
                  {sendMutation.isPending ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <Send />
                  )}
                  Approve &amp; Send
                </Button>
              </>
            )}
          </div>
        </Card>
      </div>

      <div className="flex justify-start">
        <Button variant="ghost" onClick={() => navigate('/cases')}>
          ← Back to cases
        </Button>
      </div>
    </div>
  )
}
