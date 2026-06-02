import type { ColumnMapping, FieldDefinition } from '../types'
import { API_BASE } from '../api/base'

interface Props {
  fields: FieldDefinition[]
  columns: string[]
  mapping: ColumnMapping
  onChange: (mapping: ColumnMapping) => void
}

const GROUP_LABELS: Record<string, string> = {
  demographics: 'Demographics',
  spirometry: 'Spirometry measurements',
  lung_volumes: 'Lung volume measurements',
}

export function ColumnMapper({ fields, columns, mapping, onChange }: Props) {
  const groups = ['demographics', 'spirometry', 'lung_volumes'] as const

  const setField = (key: string, col: string) => {
    onChange({ ...mapping, [key]: col || null })
  }

  const applyBmtDefaults = async () => {
    try {
      const res = await fetch(`${API_BASE}/schema/default-mapping`)
      const data = await res.json()
      onChange(data.mapping)
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-teal-900">
            Map Excel columns
          </h3>
          <p className="text-sm text-teal-700/70">
            Match each field to a column in your file. Unmapped fields are skipped.
          </p>
        </div>
        <button
          type="button"
          onClick={applyBmtDefaults}
          className="rounded-full bg-white px-4 py-2 text-sm font-medium text-teal-700 ring-1 ring-teal-200 transition hover:bg-teal-50"
        >
          Use BMT sample mapping
        </button>
      </div>

      {groups.map((group) => {
        const groupFields = fields.filter((f) => f.group === group)
        if (!groupFields.length) return null
        return (
          <div
            key={group}
            className="rounded-2xl border border-teal-100 bg-white/70 p-5 shadow-sm"
          >
            <h4 className="mb-4 text-sm font-semibold uppercase tracking-wide text-teal-600">
              {GROUP_LABELS[group]}
            </h4>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {groupFields.map((field) => (
                <label key={field.key} className="flex min-h-[5.5rem] flex-col">
                  <span className="flex items-center gap-1 text-sm font-medium text-teal-800">
                    {field.label}
                    {field.required && <span className="text-rose-500">*</span>}
                    {field.unit && (
                      <span className="text-xs font-normal text-teal-500">
                        ({field.unit})
                      </span>
                    )}
                  </span>
                  {field.hint && (
                    <span className="mt-0.5 block text-xs leading-snug text-teal-600/60">
                      {field.hint}
                    </span>
                  )}
                  <select
                    value={(mapping[field.key] as string) ?? ''}
                    onChange={(e) => setField(field.key, e.target.value)}
                    className="mt-auto w-full rounded-lg border border-teal-100 bg-white px-3 py-2 text-sm text-teal-900 outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-200"
                  >
                    <option value="">— Not mapped —</option>
                    {columns.map((col) => (
                      <option key={col} value={col}>
                        {col}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
