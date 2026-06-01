import { useState } from 'react'
import { Calculator, Loader2, Wind } from 'lucide-react'
import { calculateManual } from '../api/client'
import type { ManualCalculateResponse, Module } from '../types'
import { MeasurementGrid } from './MeasurementGrid'
import { PatternClassificationCard } from './PatternClassificationCard'
import { ResultsTable } from './ResultsTable'

const SPIRO_FIELDS = [
  { key: 'FEV1', label: 'FEV₁', unit: 'L' },
  { key: 'FVC', label: 'FVC', unit: 'L' },
  { key: 'FEV1FVC', label: 'FEV₁/FVC', unit: 'ratio or %' },
] as const

const LV_FIELDS = [
  { key: 'TLC', label: 'TLC', unit: 'L' },
  { key: 'FRC', label: 'FRC', unit: 'L' },
  { key: 'RV', label: 'RV', unit: 'L' },
  { key: 'RVTLC', label: 'RV/TLC', unit: 'ratio or %' },
  { key: 'ERV', label: 'ERV', unit: 'L' },
  { key: 'IC', label: 'IC', unit: 'L' },
  { key: 'VC', label: 'VC', unit: 'L' },
] as const

export function ManualForm() {
  const [age, setAge] = useState('40')
  const [height, setHeight] = useState('175')
  const [sex, setSex] = useState<'M' | 'F'>('M')
  const [modules, setModules] = useState<Module[]>(['spirometry', 'lung_volumes'])
  const [measured, setMeasured] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ManualCalculateResponse | null>(null)

  const toggleModule = (m: Module) => {
    setModules((prev) =>
      prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
    )
  }

  const setMeasuredField = (key: string, value: string) => {
    setMeasured((m) => ({ ...m, [key]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const measuredNums: Record<string, number> = {}
      for (const [k, v] of Object.entries(measured)) {
        if (v.trim()) measuredNums[k] = parseFloat(v)
      }
      const res = await calculateManual({
        age: parseFloat(age),
        height_cm: parseFloat(height),
        sex,
        modules,
        measured: measuredNums,
      })
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const showBoth =
    modules.includes('spirometry') && modules.includes('lung_volumes')

  return (
    <div className="space-y-8">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 md:grid-cols-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-teal-800">Age (years)</span>
            <input
              type="number"
              min={3}
              max={95}
              step={0.1}
              required
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-900 shadow-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-200"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-teal-800">Height (cm)</span>
            <input
              type="number"
              min={50}
              max={250}
              step={0.1}
              required
              value={height}
              onChange={(e) => setHeight(e.target.value)}
              className="w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-900 shadow-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-200"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-teal-800">Sex</span>
            <select
              value={sex}
              onChange={(e) => setSex(e.target.value as 'M' | 'F')}
              className="w-full rounded-xl border border-teal-200 bg-white px-4 py-2.5 text-teal-900 shadow-sm outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-200"
            >
              <option value="M">Male</option>
              <option value="F">Female</option>
            </select>
          </label>
        </div>

        <div className="flex flex-wrap gap-3">
          {(
            [
              ['spirometry', 'GLI-2022 Spirometry', Wind],
              ['lung_volumes', 'GLI-2021 Lung volumes', Calculator],
            ] as const
          ).map(([key, label, Icon]) => (
            <button
              key={key}
              type="button"
              onClick={() => toggleModule(key)}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ring-1 transition ${
                modules.includes(key)
                  ? 'bg-teal-600 text-white ring-teal-600 shadow-md shadow-teal-600/25'
                  : 'bg-white text-teal-700 ring-teal-200 hover:bg-teal-50'
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        <div
          className={
            showBoth
              ? 'grid gap-6 lg:grid-cols-2 lg:items-stretch'
              : 'max-w-3xl'
          }
        >
          {modules.includes('spirometry') && (
            <fieldset className="flex h-full flex-col rounded-2xl border border-teal-100 bg-white/60 p-5">
              <legend className="px-2 font-display text-base font-semibold text-teal-900">
                Measured spirometry
              </legend>
              <p className="mb-4 text-xs text-teal-600/80">
                Optional — leave blank for reference only
              </p>
              <MeasurementGrid
                fields={SPIRO_FIELDS}
                values={measured}
                onChange={setMeasuredField}
              />
            </fieldset>
          )}

          {modules.includes('lung_volumes') && (
            <fieldset className="flex h-full flex-col rounded-2xl border border-teal-100 bg-white/60 p-5">
              <legend className="px-2 font-display text-base font-semibold text-teal-900">
                Measured lung volumes
              </legend>
              <p className="mb-4 text-xs text-teal-600/80">
                Optional — leave blank for reference only
              </p>
              <MeasurementGrid
                fields={LV_FIELDS}
                values={measured}
                onChange={setMeasuredField}
                inputClassName="border-teal-100 focus:border-teal-400 focus:ring-teal-200"
              />
            </fieldset>
          )}
        </div>

        {error && (
          <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800 ring-1 ring-rose-200">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || modules.length === 0}
          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-teal-600 to-teal-500 px-8 py-3 font-semibold text-white shadow-lg shadow-teal-600/30 transition hover:from-teal-700 hover:to-teal-600 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Calculator className="h-5 w-5" />}
          Calculate GLI reference
        </button>
      </form>

      {result && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-teal-900/90 px-5 py-4 text-white shadow-xl">
            <p className="text-sm text-teal-100">Reference for</p>
            <p className="font-display text-xl font-semibold">
              {result.patient.sex === 'M' ? 'Male' : 'Female'},{' '}
              {result.patient.age} yrs, {result.patient.height_cm} cm
            </p>
          </div>
          {result.classification && (
            <PatternClassificationCard classification={result.classification} />
          )}
          {result.spirometry.length > 0 && (
            <ResultsTable
              title="Spirometry (GLI-2022)"
              subtitle="FEV₁, FVC, FEV₁/FVC — Bowerman et al. 2023"
              rows={result.spirometry}
            />
          )}
          {result.lung_volumes.length > 0 && (
            <ResultsTable
              title="Lung volumes (GLI-2021)"
              subtitle="TLC, FRC, RV, RV/TLC, ERV, IC, VC — Hall et al. 2021"
              rows={result.lung_volumes}
            />
          )}
        </div>
      )}
    </div>
  )
}
