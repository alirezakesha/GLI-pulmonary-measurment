import type { ParameterResult } from '../types'
import { StatusBadge } from './StatusBadge'

interface Props {
  title: string
  subtitle: string
  rows: ParameterResult[]
}

export function ResultsTable({ title, subtitle, rows }: Props) {
  if (!rows.length) return null

  return (
    <div className="overflow-hidden rounded-2xl bg-white/80 shadow-lg shadow-teal-900/5 ring-1 ring-teal-100 backdrop-blur">
      <div className="border-b border-teal-50 bg-gradient-to-r from-teal-50 to-rose-50 px-5 py-4">
        <h3 className="font-display text-lg font-semibold text-teal-900">{title}</h3>
        <p className="text-sm text-teal-700/70">{subtitle}</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead>
            <tr className="border-b border-teal-50 text-xs uppercase tracking-wide text-teal-600">
              <th className="px-4 py-3 font-semibold">Parameter</th>
              <th className="px-4 py-3 font-semibold">Measured</th>
              <th className="px-4 py-3 font-semibold">Predicted</th>
              <th className="px-4 py-3 font-semibold">LLN</th>
              <th className="px-4 py-3 font-semibold">ULN</th>
              <th className="px-4 py-3 font-semibold">% pred</th>
              <th className="px-4 py-3 font-semibold">z</th>
              <th className="px-4 py-3 font-semibold">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.parameter}
                className="border-b border-teal-50/80 transition hover:bg-teal-50/40"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-teal-900">{row.parameter}</div>
                  <div className="text-xs text-teal-600/60">
                    {row.unit === 'ratio' ? 'ratio' : row.unit}
                  </div>
                </td>
                <td className="px-4 py-3 tabular-nums font-medium">
                  {row.measured ?? '—'}
                </td>
                <td className="px-4 py-3 tabular-nums">{row.predicted}</td>
                <td className="px-4 py-3 tabular-nums text-teal-700">{row.lln}</td>
                <td className="px-4 py-3 tabular-nums">{row.uln}</td>
                <td className="px-4 py-3 tabular-nums">
                  {row.pct_pred != null ? `${row.pct_pred}%` : '—'}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {row.z_score != null ? row.z_score : '—'}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={row.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
