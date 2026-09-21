import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Loader2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { PageHeader } from '@/components/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { createMailbox } from '@/lib/api'
import type { MailboxIn } from '@/lib/types'
import { toast } from 'sonner'

interface FormState {
  name: string
  address: string
  purpose: string
  imap_host: string
  imap_port: string
  imap_security: string
  imap_folder: string
  smtp_host: string
  smtp_port: string
  smtp_security: string
  password: string
  max_emails: string
}

const INITIAL: FormState = {
  name: '',
  address: '',
  purpose: '',
  imap_host: '',
  imap_port: '993',
  imap_security: 'ssl',
  imap_folder: 'INBOX',
  smtp_host: '',
  smtp_port: '587',
  smtp_security: 'starttls',
  password: '',
  max_emails: '50',
}

function toPayload(form: FormState): MailboxIn {
  return {
    name: form.name,
    address: form.address,
    purpose: form.purpose,
    status: 'active',
    imap_host: form.imap_host,
    imap_port: Number(form.imap_port),
    imap_security: form.imap_security,
    imap_folder: form.imap_folder,
    smtp_host: form.smtp_host,
    smtp_port: Number(form.smtp_port),
    smtp_security: form.smtp_security,
    password: form.password,
    max_emails: Number(form.max_emails),
    auto_process: false,
    generate_drafts: true,
    human_approval: true,
    classifier_config_id: null,
    drafter_config_id: null,
    classifier_temperature: null,
    classifier_max_tokens: null,
    drafter_temperature: null,
    drafter_max_tokens: null,
    use_knowledge: false,
    instructions: '',
  }
}

export default function NewMailboxPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormState>(INITIAL)

  const createMutation = useMutation({
    mutationFn: createMailbox,
    onSuccess: (mailbox) => {
      toast.success('Mailbox created')
      navigate(`/mailboxes/${mailbox.id}/overview`)
    },
    onError: () => toast.error('Failed to create mailbox'),
  })

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Add Mailbox"
        description="Create a new business email context."
      />

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <StepBadge active={step === 1} done={step > 1} label="1" />
        Basics
        <span className="h-px w-8 bg-border" />
        <StepBadge active={step === 2} done={step > 2} label="2" />
        Mail Connection
        <span className="h-px w-8 bg-border" />
        <StepBadge active={step === 3} done={step > 3} label="3" />
        Review &amp; Create
      </div>

      <Card className="max-w-2xl">
        <CardContent className="flex flex-col gap-4 pt-4">
          {step === 1 && (
            <>
              <Field label="Mailbox Name">
                <Input
                  value={form.name}
                  onChange={(e) => set('name', e.target.value)}
                  placeholder="Support"
                />
              </Field>
              <Field label="Email Address">
                <Input
                  value={form.address}
                  onChange={(e) => set('address', e.target.value)}
                  placeholder="support@company.com"
                />
              </Field>
              <Field label="Purpose">
                <Input
                  value={form.purpose}
                  onChange={(e) => set('purpose', e.target.value)}
                  placeholder="Customer support enquiries"
                />
              </Field>
            </>
          )}

          {step === 2 && (
            <>
              <h3 className="text-sm font-semibold">Incoming Mail (IMAP)</h3>
              <div className="grid grid-cols-2 gap-3">
                <Field label="IMAP Server">
                  <Input
                    value={form.imap_host}
                    onChange={(e) => set('imap_host', e.target.value)}
                    placeholder="imap.company.com"
                  />
                </Field>
                <Field label="Port">
                  <Input
                    type="number"
                    value={form.imap_port}
                    onChange={(e) => set('imap_port', e.target.value)}
                  />
                </Field>
                <Field label="Security">
                  <Select
                    value={form.imap_security}
                    onValueChange={(v) => set('imap_security', v ?? 'ssl')}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ssl">SSL/TLS</SelectItem>
                      <SelectItem value="starttls">STARTTLS</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Folder">
                  <Input
                    value={form.imap_folder}
                    onChange={(e) => set('imap_folder', e.target.value)}
                  />
                </Field>
                <Field label="Password">
                  <Input
                    type="password"
                    value={form.password}
                    onChange={(e) => set('password', e.target.value)}
                    placeholder="app password"
                  />
                </Field>
                <Field label="Max messages / sync">
                  <Input
                    type="number"
                    value={form.max_emails}
                    onChange={(e) => set('max_emails', e.target.value)}
                  />
                </Field>
              </div>

              <h3 className="text-sm font-semibold">Outgoing Mail (SMTP)</h3>
              <div className="grid grid-cols-2 gap-3">
                <Field label="SMTP Server">
                  <Input
                    value={form.smtp_host}
                    onChange={(e) => set('smtp_host', e.target.value)}
                    placeholder="smtp.company.com"
                  />
                </Field>
                <Field label="Port">
                  <Input
                    type="number"
                    value={form.smtp_port}
                    onChange={(e) => set('smtp_port', e.target.value)}
                  />
                </Field>
                <Field label="Security">
                  <Select
                    value={form.smtp_security}
                    onValueChange={(v) => set('smtp_security', v ?? 'starttls')}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ssl">SSL/TLS</SelectItem>
                      <SelectItem value="starttls">STARTTLS</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="flex flex-col gap-3 text-sm">
              <SummaryRow label="Name" value={form.name} />
              <SummaryRow label="Address" value={form.address} />
              <SummaryRow label="Purpose" value={form.purpose || '—'} />
              <SummaryRow
                label="Incoming"
                value={`${form.imap_host || '—'}:${form.imap_port}`}
              />
              <SummaryRow
                label="Outgoing"
                value={`${form.smtp_host || '—'}:${form.smtp_port}`}
              />
              <div className="rounded-lg border bg-emerald-500/10 p-3 text-emerald-700 dark:text-emerald-400">
                <div className="flex items-center gap-2 font-medium">
                  <Check className="size-4" />
                  Mailbox is ready
                </div>
                <p className="text-xs text-emerald-700/80 dark:text-emerald-400/80">
                  You can configure fields, topics, knowledge and AI behaviour
                  after creation.
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-between border-t pt-4">
            <Button
              variant="outline"
              onClick={() => (step > 1 ? setStep(step - 1) : navigate('/mailboxes'))}
            >
              {step > 1 ? 'Back' : 'Cancel'}
            </Button>
            {step < 3 ? (
              <Button onClick={() => setStep(step + 1)}>Next</Button>
            ) : (
              <Button
                onClick={() => createMutation.mutate(toPayload(form))}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Check />
                )}
                Create Mailbox
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StepBadge({
  active,
  done,
  label,
}: {
  active: boolean
  done: boolean
  label: string
}) {
  return (
    <span
      className={
        active || done
          ? 'flex size-5 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground'
          : 'flex size-5 items-center justify-center rounded-full bg-muted text-xs text-muted-foreground'
      }
    >
      {done ? <Check className="size-3" /> : label}
    </span>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
