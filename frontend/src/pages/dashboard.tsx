import { useQuery } from '@tanstack/react-query'
import { Hourglass, Mail, Send, PenLine } from 'lucide-react'
import { Cell, Pie, PieChart } from 'recharts'

import { CategoryBadge } from '@/components/category-badge'
import { PageHeader } from '@/components/page-header'
import { StatCard } from '@/components/stat-card'
import { StatusBadge } from '@/components/status-badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { fetchMailboxes, fetchStats } from '@/lib/api'
import type { Stats } from '@/lib/types'
import { useState } from 'react'

const PIE_COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#94a3b8']

const EMPTY_STATS: Stats = {
  total_emails: 0,
  processed: 0,
  pending: 0,
  success_rate: 0,
  category_distribution: [],
  recent_activity: [],
}

export default function Dashboard() {
  const [mailboxFilter, setMailboxFilter] = useState('all')
  const activeMailboxId = mailboxFilter === 'all' ? undefined : Number(mailboxFilter)

  const { data: stats = EMPTY_STATS } = useQuery<Stats>({
    queryKey: ['stats', activeMailboxId],
    queryFn: () => fetchStats(activeMailboxId),
  })
  const { data: mailboxes = [] } = useQuery({
    queryKey: ['mailboxes'],
    queryFn: fetchMailboxes,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Dashboard"
        description="An overview of what the system is processing right now."
        action={
          <Select value={mailboxFilter} onValueChange={(v) => setMailboxFilter(v ?? 'all')}>
            <SelectTrigger className="w-44">
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
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Emails Today"
          value={stats.total_emails}
          description={`${stats.success_rate}% success rate`}
          icon={Mail}
          iconClassName="text-primary"
        />
        <StatCard
          label="Open Cases"
          value={stats.pending}
          description="awaiting action"
          icon={Hourglass}
          iconClassName="text-amber-600"
        />
        <StatCard
          label="Drafts"
          value={stats.processed}
          description="AI generated"
          icon={PenLine}
          iconClassName="text-blue-600"
        />
        <StatCard
          label="Sent"
          value={stats.total_emails - stats.processed - stats.pending}
          icon={Send}
          iconClassName="text-emerald-600"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Classification Distribution</CardTitle>
            <CardDescription>Incoming email by category.</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.category_distribution.length === 0 ? (
              <p className="py-6 text-sm text-muted-foreground">No data yet.</p>
            ) : (
              <ChartContainer config={{}} className="aspect-auto h-64 w-full">
                <PieChart>
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Pie
                    data={stats.category_distribution}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {stats.category_distribution.map((entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                </PieChart>
              </ChartContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>The most recently processed emails.</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.recent_activity.length === 0 ? (
              <p className="py-6 text-sm text-muted-foreground">
                No activity yet. Process an email from the Inbox.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Topic</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stats.recent_activity.map((row, index) => (
                    <TableRow key={index}>
                      <TableCell className="max-w-40 truncate font-medium">
                        {row.email}
                      </TableCell>
                      <TableCell>{row.topic}</TableCell>
                      <TableCell>
                        <CategoryBadge category={row.category} />
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={row.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
          <CardDescription>Status of core system components.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: 'Mail', status: 'Healthy' },
              { label: 'AI Model', status: 'Ready' },
              { label: 'Knowledge', status: 'Ready' },
              { label: 'Connectors', status: mailboxes.length > 0 ? 'Connected' : 'Disconnected' },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <span className="text-sm text-muted-foreground">{item.label}</span>
                <StatusBadge status={item.status} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
