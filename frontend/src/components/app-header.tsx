import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { fetchMailbox } from '@/lib/api'

interface Crumb {
  label: string
  to?: string
}

const STATIC_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  inbox: 'Inbox',
  cases: 'Cases',
  mailboxes: 'Mailboxes',
  'ai-models': 'AI Models',
  general: 'General',
  settings: 'Settings',
  overview: 'Overview',
  connection: 'Connection',
  processing: 'Processing',
  fields: 'Fields',
  topics: 'Topics',
  knowledge: 'Knowledge',
  routing: 'Routing',
  connectors: 'Connectors',
  activity: 'Activity',
}

function resolveCrumbs(pathname: string): Crumb[] {
  const segments = pathname.split('/').filter(Boolean)
  const crumbs: Crumb[] = []

  if (segments.length === 0) return crumbs

  let accumulated = ''
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i]
    accumulated += `/${segment}`
    const isLast = i === segments.length - 1
    const label = STATIC_LABELS[segment] ?? segment
    crumbs.push({
      label,
      to: isLast ? undefined : accumulated,
    })
  }

  return crumbs
}

export function AppHeader() {
  const location = useLocation()
  const navigate = useNavigate()
  const crumbs = resolveCrumbs(location.pathname)

  const [overridden, setOverridden] = useState<Record<number, string>>({})

  // Resolve dynamic segment labels (mailbox name) for nicer breadcrumbs.
  useEffect(() => {
    const segments = location.pathname.split('/').filter(Boolean)
    const mailboxIndex = segments.indexOf('mailboxes')
    if (mailboxIndex >= 0 && segments[mailboxIndex + 1]) {
      const id = Number(segments[mailboxIndex + 1])
      if (!Number.isNaN(id)) {
        let cancelled = false
        fetchMailbox(id)
          .then((mailbox) => {
            if (!cancelled) {
              setOverridden((prev) => ({ ...prev, [mailboxIndex + 1]: mailbox.name }))
            }
          })
          .catch(() => {})
        return () => {
          cancelled = true
        }
      }
    }
  }, [location.pathname])

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <Breadcrumb>
        <BreadcrumbList>
          {crumbs.map((crumb, index) => {
            const label = overridden[index] ?? crumb.label
            return (
              <BreadcrumbItem key={index}>
                {index > 0 ? <BreadcrumbSeparator /> : null}
                {crumb.to ? (
                  <button
                    className="cursor-pointer transition-colors hover:text-foreground"
                    onClick={() => navigate(crumb.to!)}
                  >
                    {label}
                  </button>
                ) : (
                  <BreadcrumbPage>{label}</BreadcrumbPage>
                )}
              </BreadcrumbItem>
            )
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </header>
  )
}
