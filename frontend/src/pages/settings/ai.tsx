import { useEffect, useState } from 'react'
import { Loader2, Pencil, Plug, Plus, Star, Trash2 } from 'lucide-react'

import { PageHeading } from '@/components/page-heading'
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
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
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
  fetchStages,
  saveStages,
  testAIConfig,
  testSavedAIConfig,
  updateAIConfig,
} from '@/lib/api'
import type {
  AIConfig,
  AIConfigIn,
  StageConfig,
  StagesSettings,
} from '@/lib/types'
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

interface StageForm {
  role: string
  goal: string
  backstory: string
  prompt: string
  max_tokens: string
  temperature: string
}

const EMPTY_STAGE: StageForm = {
  role: '',
  goal: '',
  backstory: '',
  prompt: '',
  max_tokens: '',
  temperature: '',
}

function toConfigPayload(form: ConfigForm): AIConfigIn {
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

function toStagePayload(form: StageForm): StageConfig {
  return {
    role: form.role,
    goal: form.goal,
    backstory: form.backstory,
    prompt: form.prompt,
    max_tokens: form.max_tokens === '' ? null : Number(form.max_tokens),
    temperature: form.temperature === '' ? null : Number(form.temperature),
  }
}

function stageToForm(stage: StageConfig): StageForm {
  return {
    role: stage.role,
    goal: stage.goal,
    backstory: stage.backstory,
    prompt: stage.prompt,
    max_tokens: stage.max_tokens === null ? '' : String(stage.max_tokens),
    temperature:
      stage.temperature === null ? '' : String(stage.temperature),
  }
}

export default function AISettingsPage() {
  const [configs, setConfigs] = useState<AIConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [stagesOpen, setStagesOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [hasKey, setHasKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [configForm, setConfigForm] = useState<ConfigForm>(EMPTY_CONFIG)

  const [classification, setClassification] = useState<StageForm>(EMPTY_STAGE)
  const [draft, setDraft] = useState<StageForm>(EMPTY_STAGE)
  const [savingStages, setSavingStages] = useState(false)

  async function reload() {
    try {
      const [configList, stages] = await Promise.all([
        fetchAIConfigs(),
        fetchStages(),
      ])
      setConfigs(configList)
      setClassification(stageToForm(stages.classification))
      setDraft(stageToForm(stages.draft))
    } catch {
      toast.error('Failed to load AI settings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    reload()
  }, [])

  function setConfig<K extends keyof ConfigForm>(
    key: K,
    value: ConfigForm[K],
  ) {
    setConfigForm((prev) => ({ ...prev, [key]: value }))
  }

  function setStage(
    stage: 'classification' | 'draft',
    key: keyof StageForm,
    value: string,
  ) {
    const setter = stage === 'classification' ? setClassification : setDraft
    setter((prev) => ({ ...prev, [key]: value }))
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
      const payload = toConfigPayload(configForm)
      if (editingId === null) {
        await createAIConfig(payload)
        toast.success('AI configuration created')
      } else {
        await updateAIConfig(editingId, payload)
        toast.success('AI configuration updated')
      }
      setDialogOpen(false)
      await reload()
    } catch {
      toast.error('Failed to save AI configuration')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(config: AIConfig) {
    try {
      await deleteAIConfig(config.id)
      toast.success('AI configuration deleted')
      await reload()
    } catch {
      toast.error('Failed to delete AI configuration')
    }
  }

  async function handleActivate(config: AIConfig) {
    try {
      await activateAIConfig(config.id)
      toast.success('Active configuration changed')
      await reload()
    } catch {
      toast.error('Failed to activate AI configuration')
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
      const result = await testAIConfig(toConfigPayload(configForm))
      if (result.ok) toast.success(result.message)
      else toast.error(result.message)
    } catch {
      toast.error('Test request failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveStages() {
    setSavingStages(true)
    try {
      const payload: StagesSettings = {
        classification: toStagePayload(classification),
        draft: toStagePayload(draft),
      }
      await saveStages(payload)
      toast.success('Prompts & parameters saved')
      setStagesOpen(false)
    } catch {
      toast.error('Failed to save prompts & parameters')
    } finally {
      setSavingStages(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PageHeading
          title="AI Settings"
          subtitle="Configure LLM providers and per-stage prompts"
        />
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStagesOpen(true)}>
            Prompts & Parameters
          </Button>
          <Button onClick={openCreate}>
            <Plus />
            New Config
          </Button>
        </div>
      </div>

      <Card>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 py-6 text-muted-foreground">
              <Loader2 className="animate-spin" /> Loading…
            </div>
          ) : configs.length === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">
              No AI configurations yet. Add one to use a real model.
            </p>
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
                        <span className="text-sm text-muted-foreground">
                          Inactive
                        </span>
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
                          onClick={() => handleDelete(config)}
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
              {editingId === null
                ? 'New AI Configuration'
                : 'Edit AI Configuration'}
            </DialogTitle>
            <DialogDescription>
              Configure the LLM endpoint used by the agents.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={configForm.name}
                onChange={(e) => setConfig('name', e.target.value)}
                placeholder="e.g. Local Qwen"
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
                <Label htmlFor="max_tokens">Max Tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  value={configForm.max_tokens}
                  onChange={(e) => setConfig('max_tokens', e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="temperature">Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  value={configForm.temperature}
                  onChange={(e) => setConfig('temperature', e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Switch
                checked={configForm.enabled}
                onCheckedChange={(checked) => setConfig('enabled', checked)}
              />
              <Label htmlFor="enabled">Set as active</Label>
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

      <Dialog open={stagesOpen} onOpenChange={setStagesOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Prompts & Parameters</DialogTitle>
            <DialogDescription>
              System prompt, task prompt, and generation params per stage.
              Empty fields fall back to defaults.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col gap-4">
            <StageSection
              title="Classification (分析)"
              description="Classifies each email's category, topic, and priority."
              form={classification}
              onChange={(key, value) => setStage('classification', key, value)}
              promptHint="Keep {email_content} in the prompt to inject the email."
            />
            <StageSection
              title="Draft Reply (回覆)"
              description="Drafts a professional reply from the classification."
              form={draft}
              onChange={(key, value) => setStage('draft', key, value)}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setStagesOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveStages} disabled={savingStages}>
              {savingStages ? <Loader2 className="animate-spin" /> : null}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function StageSection({
  title,
  description,
  form,
  onChange,
  promptHint,
}: {
  title: string
  description: string
  form: StageForm
  onChange: (key: keyof StageForm, value: string) => void
  promptHint?: string
}) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border p-4">
      <div className="flex flex-col gap-0.5">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="flex flex-col gap-1.5">
          <Label>Role</Label>
          <Input
            value={form.role}
            onChange={(e) => onChange('role', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Goal</Label>
          <Input
            value={form.goal}
            onChange={(e) => onChange('goal', e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Backstory</Label>
          <Input
            value={form.backstory}
            onChange={(e) => onChange('backstory', e.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>Task Prompt</Label>
        <Textarea
          value={form.prompt}
          onChange={(e) => onChange('prompt', e.target.value)}
          rows={4}
        />
        {promptHint ? (
          <p className="text-xs text-muted-foreground">{promptHint}</p>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:max-w-xs">
        <div className="flex flex-col gap-1.5">
          <Label>Max Tokens</Label>
          <Input
            type="number"
            value={form.max_tokens}
            onChange={(e) => onChange('max_tokens', e.target.value)}
            placeholder="default"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label>Temperature</Label>
          <Input
            type="number"
            step="0.1"
            value={form.temperature}
            onChange={(e) => onChange('temperature', e.target.value)}
            placeholder="default"
          />
        </div>
      </div>
    </div>
  )
}
