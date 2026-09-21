import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Plug, Plus } from 'lucide-react'

import { EmptyState } from '@/components/empty-state'
import { StatusBadge } from '@/components/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  fetchConnectors,
  fetchMailboxConnectors,
  assignConnector,
  unassignConnector,
  createConnector,
  discoverConnectorTools,
  updateConnectorPermissions,
} from '@/lib/api'
import type { MailboxConnector, ToolDescriptor } from '@/lib/types'
import { toast } from 'sonner'

const RISK_BADGE: Record<string, { tone: string; label: string }> = {
  read: { tone: 'positive', label: 'Read' },
  write: { tone: 'warning', label: 'Write' },
  destructive: { tone: 'danger', label: 'Destructive' },
}

export function ConnectorsTab({ mailboxId }: { mailboxId: number }) {
  const queryClient = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newServer, setNewServer] = useState('')
  const [managing, setManaging] = useState<MailboxConnector | null>(null)

  const { data: assigned = [] } = useQuery({
    queryKey: ['mailbox-connectors', mailboxId],
    queryFn: () => fetchMailboxConnectors(mailboxId),
  })
  const { data: allConnectors = [] } = useQuery({
    queryKey: ['connectors'],
    queryFn: fetchConnectors,
  })

  const assignedIds = new Set(assigned.map((c) => c.id))

  const createMutation = useMutation({
    mutationFn: createConnector,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connectors'] })
      setNewName('')
      setNewServer('')
      toast.success('Connector created')
    },
    onError: () => toast.error('Failed to create connector'),
  })

  const assignMutation = useMutation({
    mutationFn: (connectorId: number) =>
      assignConnector(mailboxId, connectorId, {
        enabled: true,
        allowed_tools: '',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-connectors', mailboxId] })
      toast.success('Connector enabled')
    },
    onError: () => toast.error('Failed to enable connector'),
  })

  const unassignMutation = useMutation({
    mutationFn: (connectorId: number) => unassignConnector(mailboxId, connectorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-connectors', mailboxId] })
      toast.success('Connector disabled')
    },
    onError: () => toast.error('Failed to disable connector'),
  })

  function toggle(connector: MailboxConnector) {
    if (connector.enabled) unassignMutation.mutate(connector.id)
    else assignMutation.mutate(connector.id)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          External tools available to this mailbox.
        </p>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus />
          Add Connector
        </Button>
      </div>

      {allConnectors.length === 0 && assigned.length === 0 ? (
        <EmptyState
          icon={Plug}
          title="No connectors enabled"
          description="Connect external tools that the AI can use within this mailbox."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus />
              Add Connector
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(allConnectors.length > 0 ? allConnectors : assigned).map((connector) => {
            const isAssigned = assignedIds.has(connector.id)
            return (
              <Card key={connector.id}>
                <CardContent className="flex items-center justify-between pt-4">
                  <div className="flex flex-col gap-1">
                    <span className="font-medium">{connector.name}</span>
                    <span className="text-xs text-muted-foreground capitalize">
                      {connector.type}
                      {connector.server ? ` · ${connector.server}` : ''}
                    </span>
                    <StatusBadge
                      status={isAssigned ? 'connected' : 'disconnected'}
                      label={isAssigned ? 'Enabled' : 'Disabled'}
                    />
                  </div>
                  <div className="flex gap-1">
                    {isAssigned && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setManaging(connector as MailboxConnector)}
                      >
                        Manage
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggle(connector as MailboxConnector)}
                    >
                      {isAssigned ? 'Disable' : 'Enable'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Connector</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="GitHub"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Server</Label>
              <Input
                value={newServer}
                onChange={(e) => setNewServer(e.target.value)}
                placeholder="Local GitHub MCP"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() =>
                createMutation.mutate({
                  name: newName,
                  type: 'mcp',
                  server: newServer,
                  status: 'disconnected',
                })
              }
              disabled={createMutation.isPending || !newName.trim()}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConnectorPermissionsSheet
        mailboxId={mailboxId}
        connector={managing}
        onOpenChange={(open) => {
          if (!open) setManaging(null)
        }}
      />
    </div>
  )
}

function ConnectorPermissionsSheet({
  mailboxId,
  connector,
  onOpenChange,
}: {
  mailboxId: number
  connector: MailboxConnector | null
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [tools, setTools] = useState<ToolDescriptor[] | null>(null)
  const [toggles, setToggles] = useState<Record<string, boolean>>({})

  const open = connector !== null

  const discoverMutation = useMutation({
    mutationFn: () => discoverConnectorTools(mailboxId, connector!.id),
    onSuccess: (data) => {
      setTools(data)
      const initial: Record<string, boolean> = {}
      for (const tool of data) initial[tool.name] = tool.enabled
      setToggles(initial)
    },
    onError: () => toast.error('Failed to discover tools'),
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const permissions = Object.entries(toggles).map(([name, enabled]) => ({
        tool_name: name,
        enabled,
        permission_level: 'read',
      }))
      return updateConnectorPermissions(mailboxId, connector!.id, permissions)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mailbox-connectors', mailboxId] })
      toast.success('Permissions saved')
      onOpenChange(false)
    },
    onError: () => toast.error('Failed to save permissions'),
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{connector?.name ?? ''}</SheetTitle>
          <SheetDescription>Discover and allow tools for this mailbox.</SheetDescription>
        </SheetHeader>

        {tools === null ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              Discover the tools exposed by this connector.
            </p>
            <Button
              onClick={() => discoverMutation.mutate()}
              disabled={discoverMutation.isPending}
            >
              {discoverMutation.isPending ? <Loader2 className="animate-spin" /> : null}
              Discover Tools
            </Button>
          </div>
        ) : tools.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No tools discovered. Is the connector connected?
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {tools.map((tool) => {
              const risk = RISK_BADGE[tool.risk_level] ?? RISK_BADGE.read
              return (
                <div
                  key={tool.name}
                  className="flex items-center gap-3 rounded-lg border p-3"
                >
                  <Checkbox
                    checked={toggles[tool.name] ?? false}
                    onCheckedChange={(checked) =>
                      setToggles((p) => ({ ...p, [tool.name]: Boolean(checked) }))
                    }
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="truncate text-sm font-medium">{tool.name}</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {tool.description}
                    </span>
                  </div>
                  <StatusBadge status={risk.tone} label={risk.label} />
                </div>
              )
            })}
            <Button
              className="mt-2"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? <Loader2 className="animate-spin" /> : null}
              Save Permissions
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
