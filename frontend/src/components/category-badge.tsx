import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const CATEGORY_STYLES: Record<string, string> = {
  question: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  incident: 'bg-red-500/10 text-red-700 dark:text-red-400',
  problem: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  task: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  spam: 'bg-slate-400/15 text-slate-600 dark:text-slate-400',
}

export function CategoryBadge({ category }: { category: string }) {
  const key = category.toLowerCase()
  const className = CATEGORY_STYLES[key] ?? CATEGORY_STYLES.spam
  const label = category.charAt(0).toUpperCase() + category.slice(1)

  return <Badge className={cn('border-transparent', className)}>{label}</Badge>
}
