import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'

import { EmptyState } from '@/components/empty-state'
import { StatusBadge } from '@/components/status-badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { fetchProcessingRuns, fetchProcessingStats } from '@/lib/api'
import type { ProcessingRun } from '@/lib/types'

function formatMs(ms: number | null): string {
  if (ms === null || ms === undefined) return '—'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`
}

function formatTokens(tokens: number | null): string {
  if (tokens === null || tokens === undefined) return '—'
  return tokens.toLocaleString()
}

const STAGE_LABELS: Record<string, string> = {
  email_processing: 'Email Processing',
  classification: 'Classification',
  knowledge_retrieval: 'Knowledge Retrieval',
  drafting: 'Drafting',
  mcp_tool: 'MCP Tool',
}

export function ObservabilityTab({ mailboxId }: { mailboxId: number }) {
  const { data: stats } = useQuery({
    queryKey: ['processing-stats', mailboxId],
    queryFn: () => fetchProcessingStats(mailboxId),
  })
  const { data: runs = [] } = useQuery({
    queryKey: ['processing-runs', mailboxId],
    queryFn: () => fetchProcessingRuns(mailboxId),
  })

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Processed" value={stats ? String(stats.processed) : '—'} />
        <Stat
          label="Success Rate"
          value={stats ? `${(stats.success_rate * 100).toFixed(1)}%` : '—'}
        />
        <Stat
          label="Avg Latency"
          value={stats ? formatMs(stats.average_latency_ms) : '—'}
        />
        <Stat
          label="Total Tokens"
          value={stats ? formatTokens(stats.total_tokens) : '—'}
        />
      </div>

      {runs.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No processing runs yet"
          description="Process an email to see its pipeline trace."
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Processing Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Stage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Tokens</TableHead>
                  <TableHead>Model</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => (
                  <RunRow key={run.id} run={run} />
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function RunRow({ run }: { run: ProcessingRun }) {
  return (
    <TableRow>
      <TableCell className="font-medium">
        {STAGE_LABELS[run.stage] ?? run.stage}
      </TableCell>
      <TableCell>
        <StatusBadge
          status={run.status === 'success' ? 'success' : 'failed'}
          label={run.status}
        />
      </TableCell>
      <TableCell className="text-muted-foreground">
        {formatMs(run.latency_ms)}
      </TableCell>
      <TableCell className="text-muted-foreground">
        {formatTokens(run.total_tokens)}
      </TableCell>
      <TableCell className="text-muted-foreground">
        {run.model || '—'}
      </TableCell>
    </TableRow>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-0.5 pt-4">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-2xl font-bold">{value}</span>
      </CardContent>
    </Card>
  )
}
