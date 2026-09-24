import { ChevronLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { StatusBadge } from '@/components/status-badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { Mailbox } from '@/lib/types'
import {
  MAILBOX_NAV_GROUPS,
  MAILBOX_SECTIONS,
} from './sections'

export function MailboxLocalNav({
  mailbox,
  active,
}: {
  mailbox: Mailbox
  active: string
}) {
  const navigate = useNavigate()
  const { mailboxId } = useParams<{ mailboxId: string }>()

  // System mailboxes (e.g. Legacy) only expose Overview.
  const groups = mailbox.is_system
    ? MAILBOX_NAV_GROUPS.filter((g) => g.sections.some((s) => s.value === 'overview'))
    : MAILBOX_NAV_GROUPS

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r">
      <div className="flex flex-col gap-2 border-b p-4">
        <button
          className="flex items-center gap-1 self-start text-sm text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => navigate('/mailboxes')}
        >
          <ChevronLeft className="size-4" />
          Mailboxes
        </button>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="truncate font-medium">{mailbox.name}</div>
            {mailbox.address ? (
              <div className="truncate text-xs text-muted-foreground">
                {mailbox.address}
              </div>
            ) : null}
          </div>
          <StatusBadge
            status={mailbox.is_system ? 'neutral' : mailbox.status}
            label={mailbox.is_system ? 'System' : undefined}
          />
        </div>
        {mailbox.purpose ? (
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {mailbox.purpose}
          </p>
        ) : null}
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="flex flex-col gap-4 p-2">
          {groups.map((group) => (
            <div key={group.label} className="flex flex-col gap-1">
              <div className="px-2 text-xs font-medium text-muted-foreground">
                {group.label}
              </div>
              <div className="flex flex-col gap-0.5">
                {group.sections.map((section) => (
                  <button
                    key={section.value}
                    onClick={() => navigate(`/mailboxes/${mailboxId}/${section.value}`)}
                    className={cn(
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                      active === section.value
                        ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                        : 'text-sidebar-foreground hover:bg-sidebar-accent/50',
                    )}
                  >
                    <section.icon className="size-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">{section.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </aside>
  )
}

export function resolveSection(active: string): string {
  return MAILBOX_SECTIONS.some((s) => s.value === active) ? active : 'overview'
}
