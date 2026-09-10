import { useEffect, useState } from 'react'
import { Loader2, Pencil, Plus, Trash2 } from 'lucide-react'

import { PageHeading } from '@/components/page-heading'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  createMailAccount,
  deleteMailAccount,
  fetchMailAccounts,
  updateMailAccount,
} from '@/lib/api'
import type { MailAccount, MailAccountIn } from '@/lib/types'
import { toast } from 'sonner'

interface MailForm {
  address: string
  imap_host: string
  imap_port: string
  smtp_host: string
  smtp_port: string
  password: string
  folder: string
  max_emails: string
  enabled: boolean
}

const EMPTY_FORM: MailForm = {
  address: '',
  imap_host: 'imap.gmail.com',
  imap_port: '993',
  smtp_host: 'smtp.gmail.com',
  smtp_port: '587',
  password: '',
  folder: 'INBOX',
  max_emails: '50',
  enabled: true,
}

function toPayload(form: MailForm): MailAccountIn {
  return {
    address: form.address,
    imap_host: form.imap_host,
    imap_port: Number(form.imap_port),
    smtp_host: form.smtp_host,
    smtp_port: Number(form.smtp_port),
    password: form.password,
    folder: form.folder,
    max_emails: Number(form.max_emails),
    enabled: form.enabled,
  }
}

export default function MailAccountsPage() {
  const [accounts, setAccounts] = useState<MailAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [hasPassword, setHasPassword] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<MailForm>(EMPTY_FORM)

  async function reload() {
    try {
      setAccounts(await fetchMailAccounts())
    } catch {
      toast.error('Failed to load mail accounts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  function set<K extends keyof MailForm>(key: K, value: MailForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function openCreate() {
    setEditingId(null)
    setHasPassword(false)
    setForm(EMPTY_FORM)
    setDialogOpen(true)
  }

  function openEdit(account: MailAccount) {
    setEditingId(account.id)
    setHasPassword(account.has_password)
    setForm({
      address: account.address,
      imap_host: account.imap_host,
      imap_port: String(account.imap_port),
      smtp_host: account.smtp_host,
      smtp_port: String(account.smtp_port),
      password: '',
      folder: account.folder,
      max_emails: String(account.max_emails),
      enabled: account.enabled,
    })
    setDialogOpen(true)
  }

  async function handleSave() {
    setSaving(true)
    try {
      const payload = toPayload(form)
      if (editingId === null) {
        await createMailAccount(payload)
        toast.success('Mail account created')
      } else {
        await updateMailAccount(editingId, payload)
        toast.success('Mail account updated')
      }
      setDialogOpen(false)
      await reload()
    } catch {
      toast.error('Failed to save mail account')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(account: MailAccount) {
    try {
      await deleteMailAccount(account.id)
      toast.success('Mail account deleted')
      await reload()
    } catch {
      toast.error('Failed to delete mail account')
    }
  }

  async function handleToggle(account: MailAccount) {
    try {
      await updateMailAccount(account.id, {
        address: account.address,
        imap_host: account.imap_host,
        imap_port: account.imap_port,
        smtp_host: account.smtp_host,
        smtp_port: account.smtp_port,
        password: '',
        folder: account.folder,
        max_emails: account.max_emails,
        enabled: !account.enabled,
      })
      await reload()
    } catch {
      toast.error('Failed to update mail account')
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <PageHeading
          title="Mail Accounts"
          subtitle="IMAP mailboxes the assistant fetches from"
        />
        <Button onClick={openCreate}>
          <Plus />
          New Account
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
          <CardDescription>
            The first enabled account is used for fetching.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Loader2 className="animate-spin" /> Loading…
            </div>
          ) : accounts.length === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">
              No mail accounts yet. Add one to fetch real email.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Address</TableHead>
                  <TableHead>IMAP</TableHead>
                  <TableHead>Folder</TableHead>
                  <TableHead>Max Emails</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell className="font-medium">
                      {account.address}
                    </TableCell>
                    <TableCell>
                      {account.imap_host}:{account.imap_port}
                    </TableCell>
                    <TableCell>{account.folder}</TableCell>
                    <TableCell>{account.max_emails}</TableCell>
                    <TableCell>
                      <Switch
                        checked={account.enabled}
                        onCheckedChange={() => handleToggle(account)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => openEdit(account)}
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleDelete(account)}
                        >
                          <Trash2 />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingId === null ? 'New Mail Account' : 'Edit Mail Account'}
            </DialogTitle>
            <DialogDescription>
              Configure IMAP access for fetching emails.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="address">Email Address</Label>
              <Input
                id="address"
                value={form.address}
                onChange={(e) => set('address', e.target.value)}
                placeholder="support@example.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="imap_host">IMAP Host</Label>
                <Input
                  id="imap_host"
                  value={form.imap_host}
                  onChange={(e) => set('imap_host', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="imap_port">IMAP Port</Label>
                <Input
                  id="imap_port"
                  type="number"
                  value={form.imap_port}
                  onChange={(e) => set('imap_port', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="smtp_host">SMTP Host</Label>
                <Input
                  id="smtp_host"
                  value={form.smtp_host}
                  onChange={(e) => set('smtp_host', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="smtp_port">SMTP Port</Label>
                <Input
                  id="smtp_port"
                  type="number"
                  value={form.smtp_port}
                  onChange={(e) => set('smtp_port', e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                placeholder={
                  hasPassword ? '•••••• (leave blank to keep)' : 'app password'
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="folder">Folder</Label>
                <Input
                  id="folder"
                  value={form.folder}
                  onChange={(e) => set('folder', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="max_emails">Max Emails</Label>
                <Input
                  id="max_emails"
                  type="number"
                  value={form.max_emails}
                  onChange={(e) => set('max_emails', e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                checked={form.enabled}
                onCheckedChange={(checked) => set('enabled', checked)}
              />
              <Label htmlFor="enabled">Enabled</Label>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="animate-spin" /> : null}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
