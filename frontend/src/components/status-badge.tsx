import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type Tone = 'positive' | 'warning' | 'danger' | 'neutral' | 'info'

const TONES: Record<Tone, string> = {
  positive: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  warning: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  danger: 'bg-red-500/10 text-red-600 dark:text-red-400',
  neutral: 'bg-slate-400/15 text-slate-600 dark:text-slate-400',
  info: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
}

const STATUS_TONE: Record<string, Tone> = {
  active: 'positive',
  healthy: 'positive',
  ready: 'positive',
  connected: 'positive',
  sent: 'positive',
  processed: 'positive',
  indexing: 'info',
  draft: 'info',
  new: 'info',
  degraded: 'warning',
  warning: 'warning',
  disabled: 'neutral',
  disconnected: 'neutral',
  failed: 'danger',
  error: 'danger',
}

export function statusTone(status: string): Tone {
  const key = status.toLowerCase()
  return STATUS_TONE[key] ?? 'neutral'
}

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string
  label?: string
  className?: string
}) {
  const tone = statusTone(status)
  const text = label ?? status

  return (
    <Badge className={cn('border-transparent capitalize', TONES[tone], className)}>
      {text}
    </Badge>
  )
}
