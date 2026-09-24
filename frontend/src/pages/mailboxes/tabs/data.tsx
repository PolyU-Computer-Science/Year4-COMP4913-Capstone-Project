import { useNavigate, useParams } from 'react-router-dom'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { FieldsTab } from './fields'
import { KnowledgeTab } from './knowledge'
import { TopicsTab } from './topics'

const SUB_TABS = [
  { value: 'topics', label: 'Topics' },
  { value: 'fields', label: 'Custom fields' },
  { value: 'knowledge', label: 'Knowledge' },
]

export function DataTab({ mailboxId }: { mailboxId: number }) {
  const navigate = useNavigate()
  const { sub = 'topics' } = useParams<{ sub?: string }>()

  const active = SUB_TABS.some((t) => t.value === sub) ? sub : 'topics'

  return (
    <div className="flex flex-col gap-4">
      <Tabs
        value={active}
        onValueChange={(value) => navigate(`/mailboxes/${mailboxId}/data/${value}`)}
      >
        <TabsList variant="line" className="w-fit">
          {SUB_TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="pt-1">
        {active === 'topics' && <TopicsTab mailboxId={mailboxId} />}
        {active === 'fields' && <FieldsTab mailboxId={mailboxId} />}
        {active === 'knowledge' && <KnowledgeTab mailboxId={mailboxId} />}
      </div>
    </div>
  )
}
