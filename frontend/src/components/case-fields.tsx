import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Pencil } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { fetchCaseFields, updateCaseFields } from '@/lib/api'
import type { CaseField } from '@/lib/types'
import { toast } from 'sonner'

export function CaseFields({ caseId }: { caseId: string }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Record<string, unknown>>({})

  const { data: fields = [] } = useQuery({
    queryKey: ['case-fields', caseId],
    queryFn: () => fetchCaseFields(caseId),
    enabled: !!caseId,
  })

  useEffect(() => {
    if (!editing) {
      const values: Record<string, unknown> = {}
      for (const field of fields) {
        if (field.value !== null && field.value !== undefined) {
          values[String(field.field_id)] = field.value
        }
      }
      setDraft(values)
    }
  }, [fields, editing])

  const saveMutation = useMutation({
    mutationFn: () => updateCaseFields(caseId, draft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-fields', caseId] })
      setEditing(false)
      toast.success('Fields saved')
    },
    onError: (error) => {
      const detail = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      toast.error(detail ?? 'Failed to save fields')
    },
  })

  if (fields.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Custom Fields</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No custom fields configured for this mailbox.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Custom Fields</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {fields.map((field) => {
          const key = String(field.field_id)
          const value = draft[key]

          return (
            <div key={field.field_id} className="flex items-center justify-between gap-3">
              <span className="w-36 shrink-0 text-sm text-muted-foreground">
                {field.name}
                {field.required ? <span className="text-destructive"> *</span> : null}
              </span>
              {editing ? (
                <FieldEditor
                  field={field}
                  value={value}
                  onChange={(v) => setDraft((p) => ({ ...p, [key]: v }))}
                />
              ) : (
                <span className="flex-1 text-sm font-medium">
                  {field.value === null || field.value === undefined
                    ? '—'
                    : String(field.value)}
                </span>
              )}
            </div>
          )
        })}

        <div className="flex justify-end gap-2 border-t pt-3">
          {editing ? (
            <>
              <Button variant="outline" onClick={() => setEditing(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? <Loader2 className="animate-spin" /> : null}
                Save
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              <Pencil />
              Edit
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function FieldEditor({
  field,
  value,
  onChange,
}: {
  field: CaseField
  value: unknown
  onChange: (value: unknown) => void
}) {
  if (field.type === 'boolean') {
    return (
      <Switch
        checked={Boolean(value)}
        onCheckedChange={(v) => onChange(v)}
      />
    )
  }

  if (field.type === 'select' && field.options.length > 0) {
    return (
      <Select
        value={value === undefined || value === '' ? undefined : String(value)}
        onValueChange={(v) => onChange(v)}
      >
        <SelectTrigger className="w-full">
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {field.options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }

  if (field.type === 'number') {
    return (
      <Input
        type="number"
        className="w-full"
        value={value === undefined ? '' : String(value)}
        onChange={(e) => onChange(e.target.value)}
      />
    )
  }

  return (
    <Input
      className="w-full"
      value={value === undefined ? '' : String(value)}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}
