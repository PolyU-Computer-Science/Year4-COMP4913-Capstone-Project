import { useEffect, useState } from 'react'
import { Loader2, Pencil, Plug, Plus, Star, Trash2 } from 'lucide-react'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  activateAIConfig,
  createAIConfig,
  deleteAIConfig,
  fetchAIConfigs,
  testAIConfig,
  testSavedAIConfig,
  updateAIConfig,
} from '@/lib/api'
import type { AIConfig, AIConfigIn } from '@/lib/types'
import { toast } from 'sonner'

const PROVIDERS = [
  'local',
  'openai',
  'openrouter',
  'anthropic',
  'groq',
  'deepseek',
  'google',
]

interface ConfigForm {
  name: string
  provider: string
  model: string
  base_url: string
  api_key: string
  timeout: string
  max_tokens: string
  temperature: string
  enabled: boolean
}

const EMPTY_CONFIG: ConfigForm = {
  name: '',
  provider: 'local',
  model: '',
  base_url: '',
  api_key: '',
  timeout: '120',
  max_tokens: '8000',
  temperature: '0.2',
  enabled: true,
}

function toPayload(form: ConfigForm): AIConfigIn {
  return {
    name: form.name,
    provider: form.provider,
    model: form.model,
    base_url: form.base_url,
    api_key: form.api_key,
    timeout: Number(form.timeout),
    max_tokens: Number(form.max_tokens),
    temperature: Number(form.temperature),
    enabled: form.enabled,
  }
}

function configToForm(config: AIConfig): ConfigForm {
  return {
    name: config.name,
    provider: config.provider,
    model: config.model,
    base_url: config.base_url,
    api_key: '',
    timeout: String(config.timeout),
    max_tokens: String(config.max_tokens),
    temperature: String(config.temperature),
    enabled: config.enabled,
  }
}

export default function AIModelsPage() {
  const [configs, setConfigs] = useState<AIConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [hasKey, setHasKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [toDelete, setToDelete] = useState<AIConfig | null>(null)
  const [configForm, setConfigForm] = useState<ConfigForm>(EMPTY_CONFIG)

  async function reload() {
    try {
      setConfigs(await fetchAIConfigs())
    } catch {
      toast.error('Failed to load AI models')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  function setConfig<K extends keyof ConfigForm>(key: K, value: ConfigForm[K]) {
    setConfigForm((prev) => ({ ...prev, [key]: value }))
  }

  function openCreate() {
    setEditingId(null)
    setHasKey(false)
    setConfigForm(EMPTY_CONFIG)
    setDialogOpen(true)
  }

  function openEdit(config: AIConfig) {
    setEditingId(config.id)
    setHasKey(config.has_api_key)
    setConfigForm(configToForm(config))
    setDialogOpen(true)
  }

  async function handleSave() {
    setSaving(true)
    try {
      const payload = toPayload(configForm)
      if (editingId === null) {
        await createAIConfig(payload)
        toast.success('AI model created')
      } else {
        await updateAIConfig(editingId, payload)
        toast.success('AI model updated')
      }
      setDialogOpen(false)
      await reload()
    } catch {
      toast.error('Failed to save AI model')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(config: AIConfig) {
    try {
      await deleteAIConfig(config.id)
      toast.success('AI model deleted')
      await reload()
    } catch {
      toast.error('Failed to delete AI model')
    }
  }

  async function handleActivate(config: AIConfig) {
    try {
      await activateAIConfig(config.id)
      toast.success('Active model changed')
      await reload()
    } catch {
      toast.error('Failed to activate AI model')
    }
  }

  async function handleTestRow(config: AIConfig) {
    setTestingId(config.id)
    try {
      const result = await testSavedAIConfig(config.id)
      if (result.ok) toast.success(result.message)
      else toast.error(result.message)
    } catch {
      toast.error('Test request failed')
    } finally {
      setTestingId(null)
    }
  }

  async function handleTestDialog() {
    setSaving(true)
    try {
      const result = await testAIConfig(toPayload(configForm))
      if (result.ok) toast.success(result.message)
      else toast.error(result.message)
    } catch {
      toast.error('Test request failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="AI Models"
        description="Manage model configurations available to mailboxes."
        action={
          <Button onClick={openCreate}>
            <Plus />
            Add Model
          </Button>
        }
      />

      <Card>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Loader2 className="animate-spin" /> Loading…
            </div>
          ) : configs.length === 0 ? (
            <EmptyState
              icon={Plug}
              title="No AI models"
              description="Add a model configuration to power classification and drafting."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">{config.name}</TableCell>
                    <TableCell>{config.provider}</TableCell>
                    <TableCell>{config.model}</TableCell>
                    <TableCell>
                      {config.enabled ? (
                        <Badge className="border-transparent bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                          <Star className="size-3" />
                          Active
                        </Badge>
                      ) : (
                        <StatusBadge status="neutral" label="Inactive" />
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {!config.enabled && (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleActivate(config)}
                            title="Set active"
                          >
                            <Star />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleTestRow(config)}
                          disabled={testingId === config.id}
                          title="Test connection"
                        >
                          {testingId === config.id ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <Plug />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => openEdit(config)}
                        >
                          <Pencil />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setToDelete(config)}
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
              {editingId === null ? 'Add AI Model' : 'Edit AI Model'}
            </DialogTitle>
            <DialogDescription>
              Configure the LLM endpoint used by agents.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={configForm.name}
                onChange={(e) => setConfig('name', e.target.value)}
                placeholder="e.g. OpenAI Main"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="provider">Provider</Label>
              <Select
                value={configForm.provider}
                onValueChange={(value) => setConfig('provider', value ?? 'local')}
              >
                <SelectTrigger id="provider" className="w-full">
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((provider) => (
                    <SelectItem key={provider} value={provider}>
                      {provider}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="model">Model</Label>
              <Input
                id="model"
                value={configForm.model}
                onChange={(e) => setConfig('model', e.target.value)}
                placeholder="e.g. gpt-4o-mini"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="base_url">Base URL</Label>
              <Input
                id="base_url"
                value={configForm.base_url}
                onChange={(e) => setConfig('base_url', e.target.value)}
                placeholder="e.g. https://api.openai.com/v1"
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="api_key">API Key</Label>
              <Input
                id="api_key"
                type="password"
                value={configForm.api_key}
                onChange={(e) => setConfig('api_key', e.target.value)}
                placeholder={hasKey ? '•••••• (leave blank to keep)' : 'sk-...'}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="timeout">Timeout (s)</Label>
              <Input
                id="timeout"
                type="number"
                value={configForm.timeout}
                onChange={(e) => setConfig('timeout', e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-2">
                <Label htmlFor="max_tokens">Default Max Tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  value={configForm.max_tokens}
                  onChange={(e) => setConfig('max_tokens', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="temperature">Default Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  value={configForm.temperature}
                  onChange={(e) => setConfig('temperature', e.target.value)}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleTestDialog}
              disabled={saving}
            >
              {saving ? <Loader2 className="animate-spin" /> : <Plug />}
              Test
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="animate-spin" /> : null}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={toDelete !== null}
        onOpenChange={(open) => {
          if (!open) setToDelete(null)
        }}
        title={`Delete ${toDelete?.name ?? 'model'}?`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (toDelete) handleDelete(toDelete)
        }}
      />
    </div>
  )
}
