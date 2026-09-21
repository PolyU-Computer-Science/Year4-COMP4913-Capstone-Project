import {
  FolderOpen,
  HelpCircle,
  Inbox,
  LayoutDashboard,
  MailCheck,
  Mailbox,
  Sparkles,
  Settings,
} from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { fetchEmails } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

const WORKSPACE_ITEMS = [
  { title: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { title: 'Inbox', icon: Inbox, path: '/inbox' },
  { title: 'Cases', icon: FolderOpen, path: '/cases' },
  { title: 'Mailboxes', icon: Mailbox, path: '/mailboxes' },
]

const SYSTEM_ITEMS = [
  { title: 'AI Models', icon: Sparkles, path: '/settings/ai-models' },
  { title: 'General', icon: Settings, path: '/settings/general' },
]

function useInboxCount() {
  const { data: emails = [] } = useQuery({
    queryKey: ['emails'],
    queryFn: () => fetchEmails(),
    staleTime: 10_000,
  })

  return emails.filter(
    (email) => email.status === 'new' || email.status === 'processed',
  ).length
}

function NavGroup({
  label,
  items,
}: {
  label: string
  items: typeof WORKSPACE_ITEMS
}) {
  const location = useLocation()
  const navigate = useNavigate()
  const inboxCount = useInboxCount()

  function isActive(path: string): boolean {
    if (path === '/dashboard') return location.pathname === '/dashboard'
    return location.pathname === path || location.pathname.startsWith(`${path}/`)
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                isActive={isActive(item.path)}
                tooltip={item.title}
                onClick={() => navigate(item.path)}
              >
                <item.icon />
                <span>{item.title}</span>
              </SidebarMenuButton>
              {item.title === 'Inbox' && inboxCount > 0 && (
                <SidebarMenuBadge>{inboxCount}</SidebarMenuBadge>
              )}
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="pointer-events-none">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <MailCheck className="size-4" />
              </div>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5 leading-none group-data-[collapsible=icon]:hidden">
                <span className="truncate font-semibold">Agentic Mail</span>
                <span className="truncate text-xs text-muted-foreground">
                  AI Email Assistant
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavGroup label="Workspace" items={WORKSPACE_ITEMS} />
        <NavGroup label="System" items={SYSTEM_ITEMS} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Help">
              <HelpCircle />
              <span>Help</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
