import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Gauge, Hourglass, Mail } from 'lucide-react'
import { Cell, Pie, PieChart } from 'recharts'

import { CategoryBadge } from '@/components/category-badge'
import { PageHeading } from '@/components/page-heading'
import { StatCard } from '@/components/stat-card'
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
import { fetchStats } from '@/lib/api'
import type { Stats } from '@/lib/types'

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
  const { data: stats = EMPTY_STATS } = useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: fetchStats,
  })

  return (
    <div className="flex flex-col gap-4">
      <PageHeading
        title="Dashboard"
        subtitle="Overview of your email assistant"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total Emails"
          value={stats.total_emails}
          icon={Mail}
          iconClassName="text-primary"
        />
        <StatCard
          label="Processed"
          value={stats.processed}
          description="completed"
          icon={CheckCircle2}
          iconClassName="text-emerald-600"
        />
        <StatCard
          label="Pending"
          value={stats.pending}
          description="awaiting action"
          icon={Hourglass}
          iconClassName="text-amber-600"
        />
        <StatCard
          label="Success Rate"
          value={`${stats.success_rate}%`}
          icon={Gauge}
          iconClassName="text-blue-600"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>The most recently processed emails.</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.recent_activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No activity yet. Process an email from the Inbox.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Topic</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.recent_activity.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{row.email}</TableCell>
                    <TableCell>{row.topic}</TableCell>
                    <TableCell>
                      <CategoryBadge category={row.category} />
                    </TableCell>
                    <TableCell>{row.priority}</TableCell>
                    <TableCell>{row.status}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Category Distribution</CardTitle>
          <CardDescription>Incoming email by classification.</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.category_distribution.length === 0 ? (
            <p className="text-sm text-muted-foreground">No data yet.</p>
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
    </div>
  )
}
