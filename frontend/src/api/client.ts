import type {
  BatchCalculateResponse,
  BatchPreviewResponse,
  ColumnMapping,
  ManualCalculateResponse,
  MeasuredValues,
  Module,
} from '../types'

const API = '/api'

export async function calculateManual(body: {
  age: number
  height_cm: number
  sex: 'M' | 'F'
  modules: Module[]
  measured: MeasuredValues
}): Promise<ManualCalculateResponse> {
  const res = await fetch(`${API}/calculate/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Calculation failed')
  }
  return res.json()
}

export async function previewBatch(file: File): Promise<BatchPreviewResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/batch/preview`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Preview failed')
  }
  return res.json()
}

export async function calculateBatch(
  file: File,
  mapping: ColumnMapping,
  modules: Module[],
): Promise<BatchCalculateResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('mapping', JSON.stringify(mapping))
  form.append('modules', JSON.stringify(modules))
  const res = await fetch(`${API}/batch/calculate`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Batch calculation failed')
  }
  return res.json()
}

export async function fetchFields() {
  const res = await fetch(`${API}/schema/fields`)
  return res.json()
}

export async function fetchDefaultMapping() {
  const res = await fetch(`${API}/schema/default-mapping`)
  return res.json()
}
