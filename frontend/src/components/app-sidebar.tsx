import {
  FolderOpen,
  Inbox,
  LayoutDashboard,
  Mail,
  MailCheck,
  Settings2,
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
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'

const MAIN_ITEMS = [
  { title: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { title: 'Inbox', icon: Inbox, path: '/inbox' },
  { title: 'Cases', icon: FolderOpen, path: '/cases' },
]

const SETTINGS_ITEMS = [
  { title: 'AI Settings', icon: Settings2, path: '/settings/ai' },
  { title: 'Mail Accounts', icon: Mail, path: '/settings/mail' },
]

function NavGroup({
  label,
  items,
}: {
  label: string
  items: typeof MAIN_ITEMS
}) {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                isActive={location.pathname === item.path}
                onClick={() => navigate(item.path)}
              >
                <item.icon />
                <span>{item.title}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 pt-2 pb-1">
          <MailCheck className="size-6 text-primary" />
          <span className="text-lg font-bold">Email Assistant</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <NavGroup label="Main" items={MAIN_ITEMS} />
        <NavGroup label="Settings" items={SETTINGS_ITEMS} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarSeparator />
        <p className="px-3 pb-2 text-xs text-muted-foreground">
          AI Email Assistant · v1.0
        </p>
      </SidebarFooter>
    </Sidebar>
  )
}
