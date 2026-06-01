import { useCallback, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
} from 'lucide-react'
import { calculateBatch, previewBatch } from '../api/client'
import type {
  BatchCalculateResponse,
  BatchPreviewResponse,
  ColumnMapping,
  Module,
} from '../types'
import { downloadBase64Excel } from '../utils/download'
import { ColumnMapper } from './ColumnMapper'
import { PatternClassificationCard } from './PatternClassificationCard'
import { PatientGliReport } from './PatientGliReport'

type Step = 'upload' | 'map' | 'results'

export function BatchUpload() {
  const [step, setStep] = useState<Step>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<BatchPreviewResponse | null>(null)
  const [mapping, setMapping] = useState<ColumnMapping>({})
  const [modules, setModules] = useState<Module[]>(['spirometry', 'lung_volumes'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [batchResult, setBatchResult] = useState<BatchCalculateResponse | null>(null)

  const onDrop = useCallback(async (f: File) => {
    if (!f.name.match(/\.xlsx?$/i)) {
      setError('Please upload an Excel file (.xlsx)')
      return
    }
    setFile(f)
    setError(null)
    setLoading(true)
    try {
      const p = await previewBatch(f)
      setPreview(p)
      setMapping(p.suggested_mapping)
      setStep('map')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) onDrop(f)
  }

  const runBatch = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const res = await calculateBatch(file, mapping, modules)
      setBatchResult(res)
      downloadBase64Excel(res.excel_base64, res.output_filename)
      setStep('results')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch failed')
    } finally {
      setLoading(false)
    }
  }

  const downloadExcelAgain = () => {
    if (!batchResult) return
    downloadBase64Excel(batchResult.excel_base64, batchResult.output_filename)
  }

  const reset = () => {
    setStep('upload')
    setFile(null)
    setPreview(null)
    setBatchResult(null)
    setError(null)
  }

  return (
    <div className="space-y-8">
      {step === 'upload' && (
        <div
          className="relative flex flex-col items-center justify-center rounded-3xl border-2 border-dashed border-teal-300 bg-white/50 px-8 py-16 text-center transition hover:border-teal-400 hover:bg-white/80"
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            const f = e.dataTransfer.files[0]
            if (f) onDrop(f)
          }}
        >
          <div className="mb-4 rounded-2xl bg-teal-100 p-4 text-teal-600">
            <Upload className="h-10 w-10" />
          </div>
          <h3 className="font-display text-xl font-semibold text-teal-900">
            Drop your PFT Excel file here
          </h3>
          <p className="mt-2 max-w-md text-sm text-teal-700/70">
            Your original spreadsheet is returned with new <strong>GLI_*</strong> columns
            (Predicted, LLN, ULN, z, % pred, Status) appended to each row.
          </p>
          <label className="mt-6 cursor-pointer rounded-full bg-teal-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-teal-700">
            Choose file
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={handleFileInput}
            />
          </label>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center rounded-3xl bg-white/80">
              <Loader2 className="h-8 w-8 animate-spin text-teal-600" />
            </div>
          )}
        </div>
      )}

      {step === 'map' && preview && file && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-4 rounded-2xl bg-white/80 px-5 py-4 ring-1 ring-teal-100">
            <FileSpreadsheet className="h-8 w-8 text-teal-600" />
            <div className="flex-1">
              <p className="font-medium text-teal-900">{preview.filename}</p>
              <p className="text-sm text-teal-600">
                {preview.row_count} rows · {preview.columns.length} columns
              </p>
            </div>
            <button
              type="button"
              onClick={reset}
              className="text-sm text-teal-600 underline hover:text-teal-800"
            >
              Change file
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {(['spirometry', 'lung_volumes'] as Module[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() =>
                  setModules((prev) =>
                    prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
                  )
                }
                className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${
                  modules.includes(m)
                    ? 'bg-teal-600 text-white ring-teal-600'
                    : 'bg-white text-teal-700 ring-teal-200'
                }`}
              >
                {m === 'spirometry' ? 'GLI-2022 Spirometry' : 'GLI-2021 Lung volumes'}
              </button>
            ))}
          </div>

          <ColumnMapper
            fields={preview.available_fields}
            columns={preview.columns}
            mapping={mapping}
            onChange={setMapping}
          />

          <button
            type="button"
            disabled={loading || modules.length === 0}
            onClick={runBatch}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-rose-500 to-teal-600 px-8 py-3 font-semibold text-white shadow-lg transition hover:opacity-95 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-5 w-5" />
            )}
            Add GLI columns & download Excel
          </button>
        </div>
      )}

      {step === 'results' && batchResult && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-gradient-to-r from-teal-800 to-teal-700 px-6 py-5 text-white">
            <div>
              <p className="text-sm text-teal-100">Your file is ready</p>
              <p className="font-display text-2xl font-semibold">
                {batchResult.output_filename}
              </p>
              <p className="mt-1 text-sm text-teal-100/90">
                {batchResult.processed} rows with GLI columns · {batchResult.skipped}{' '}
                skipped · {batchResult.added_columns.length} new columns
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={downloadExcelAgain}
                className="inline-flex items-center gap-2 rounded-full bg-white/20 px-4 py-2 text-sm font-medium backdrop-blur hover:bg-white/30"
              >
                <Download className="h-4 w-4" />
                Download Excel again
              </button>
              <button
                type="button"
                onClick={reset}
                className="rounded-full bg-white px-4 py-2 text-sm font-medium text-teal-800"
              >
                New upload
              </button>
            </div>
          </div>

          <p className="text-sm text-teal-700/80">
            New columns include GLI predicted / LLN / ULN / z / status per parameter, plus{' '}
            <code className="rounded bg-teal-50 px-1">GLI_PFT_Pattern</code> (normal, obstruction,
            restriction, or mixed) based on FEV₁/FVC and TLC vs LLN.
          </p>

          <div className="space-y-3">
            {batchResult.results.map((row) => (
              <details
                key={row.row_index}
                className="group rounded-2xl bg-white/80 ring-1 ring-teal-100 open:shadow-md"
              >
                <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4">
                  <span className="font-mono text-xs text-teal-500">#{row.row_index + 1}</span>
                  <span className="font-medium text-teal-900">
                    {row.patient_id ?? 'Unknown patient'}
                  </span>
                  {row.sex && row.age != null && (
                    <span className="text-sm text-teal-600">
                      {row.sex}, {row.age} yrs, {row.height_cm} cm
                    </span>
                  )}
                  {row.classification && (
                    <PatternClassificationCard
                      classification={row.classification}
                      compact
                    />
                  )}
                  {row.flags.length > 0 && (
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-medium text-rose-700">
                      {row.flags.length} flag{row.flags.length > 1 ? 's' : ''}
                    </span>
                  )}
                  {row.errors.length > 0 && !row.spirometry.length && !row.lung_volumes.length && (
                    <AlertCircle className="ml-auto h-4 w-4 text-amber-500" />
                  )}
                </summary>
                <div className="space-y-4 border-t border-teal-50 px-5 pb-5">
                  {row.errors.length > 0 && (
                    <div className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      {row.errors.join(' · ')}
                    </div>
                  )}
                  {row.flags.length > 0 && (
                    <ul className="flex flex-wrap gap-2">
                      {row.flags.map((f) => (
                        <li
                          key={f}
                          className="rounded-full bg-rose-50 px-2 py-0.5 text-xs text-rose-700"
                        >
                          {f}
                        </li>
                      ))}
                    </ul>
                  )}
                  {row.classification && (
                    <PatternClassificationCard classification={row.classification} />
                  )}
                  <PatientGliReport
                    spirometry={row.spirometry}
                    lungVolumes={row.lung_volumes}
                  />
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}
    </div>
  )
}
