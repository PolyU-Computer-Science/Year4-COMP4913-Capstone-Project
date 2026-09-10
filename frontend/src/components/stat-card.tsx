import type { LucideIcon } from 'lucide-react'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  description?: string
  icon: LucideIcon
  iconClassName?: string
}

export function StatCard({
  label,
  value,
  description,
  icon: Icon,
  iconClassName,
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs font-medium text-muted-foreground">
            {label}
          </span>
          <span className="text-2xl font-bold">{value}</span>
          {description ? (
            <span className="text-xs text-muted-foreground">{description}</span>
          ) : null}
        </div>
        <Icon className={cn('size-8', iconClassName)} />
      </CardContent>
    </Card>
  )
}
