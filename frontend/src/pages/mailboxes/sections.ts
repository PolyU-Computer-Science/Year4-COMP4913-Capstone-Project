import {
  Activity,
  BookOpen,
  Cable,
  LayoutDashboard,
  ListTree,
  Plug,
  Route,
  Sparkles,
  Tags,
  type LucideIcon,
} from 'lucide-react'

export interface MailboxSection {
  value: string
  label: string
  icon: LucideIcon
  description: string
}

export interface MailboxNavGroup {
  label: string
  sections: MailboxSection[]
}

export const MAILBOX_NAV_GROUPS: MailboxNavGroup[] = [
  {
    label: 'Mailbox',
    sections: [
      {
        value: 'overview',
        label: 'Overview',
        icon: LayoutDashboard,
        description: 'Status and configuration summary.',
      },
      {
        value: 'connection',
        label: 'Connection',
        icon: Cable,
        description: 'Configure incoming and outgoing email services.',
      },
      {
        value: 'processing',
        label: 'Processing',
        icon: Sparkles,
        description: 'Configure how AI processes messages in this mailbox.',
      },
    ],
  },
  {
    label: 'Data',
    sections: [
      {
        value: 'topics',
        label: 'Topics',
        icon: Tags,
        description: 'Classification taxonomy for this mailbox.',
      },
      {
        value: 'fields',
        label: 'Custom Fields',
        icon: ListTree,
        description: 'Case data schema for this mailbox.',
      },
      {
        value: 'knowledge',
        label: 'Knowledge',
        icon: BookOpen,
        description: 'Manage information available to this mailbox.',
      },
    ],
  },
  {
    label: 'Automation',
    sections: [
      {
        value: 'routing',
        label: 'Routing',
        icon: Route,
        description: 'Map classified work to teams and agents.',
      },
    ],
  },
  {
    label: 'Integrations',
    sections: [
      {
        value: 'connectors',
        label: 'Connectors',
        icon: Plug,
        description: 'External tools and MCP connectors.',
      },
    ],
  },
  {
    label: 'Monitoring',
    sections: [
      {
        value: 'activity',
        label: 'Activity',
        icon: Activity,
        description: 'Processing, routing, and tool history.',
      },
    ],
  },
]

export const MAILBOX_SECTIONS: MailboxSection[] = MAILBOX_NAV_GROUPS.flatMap(
  (group) => group.sections,
)

export const MAILBOX_SECTION_MAP: Record<string, MailboxSection> =
  Object.fromEntries(MAILBOX_SECTIONS.map((s) => [s.value, s]))
