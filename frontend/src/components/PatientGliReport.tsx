import type { ParameterResult } from '../types'
import { StatusBadge } from './StatusBadge'

interface Props {
  spirometry: ParameterResult[]
  lungVolumes: ParameterResult[]
}

const COL_WIDTHS = {
  param: 'w-[14%]',
  num: 'w-[10%]',
  status: 'w-[16%]',
} as const

function DataRow({ r }: { r: ParameterResult }) {
  return (
    <tr className="border-t border-teal-50">
      <td className={`px-3 py-2 font-medium text-teal-900 ${COL_WIDTHS.param}`}>
        {r.parameter}
      </td>
      <td className={`px-3 py-2 text-right tabular-nums ${COL_WIDTHS.num}`}>
        {r.measured ?? '—'}
      </td>
      <td className={`px-3 py-2 text-right tabular-nums ${COL_WIDTHS.num}`}>
        {r.predicted}
      </td>
      <td className={`px-3 py-2 text-right tabular-nums text-teal-700 ${COL_WIDTHS.num}`}>
        {r.lln}
      </td>
      <td className={`px-3 py-2 text-right tabular-nums ${COL_WIDTHS.num}`}>{r.uln}</td>
      <td className={`px-3 py-2 text-right tabular-nums ${COL_WIDTHS.num}`}>
        {r.pct_pred != null ? `${r.pct_pred}%` : '—'}
      </td>
      <td className={`px-3 py-2 text-right tabular-nums ${COL_WIDTHS.num}`}>
        {r.z_score ?? '—'}
      </td>
      <td className={`px-3 py-2 text-right ${COL_WIDTHS.status}`}>
        <StatusBadge status={r.status} />
      </td>
    </tr>
  )
}

function SectionHeader({ title }: { title: string }) {
  return (
    <tr className="bg-teal-50/60">
      <td
        colSpan={8}
        className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-teal-600"
      >
        {title}
      </td>
    </tr>
  )
}

/**
 * Single table for spirometry + lung volumes so columns stay aligned.
 */
export function PatientGliReport({ spirometry, lungVolumes }: Props) {
  if (!spirometry.length && !lungVolumes.length) return null

  return (
    <div className="overflow-x-auto rounded-xl ring-1 ring-teal-100">
      <table className="w-full table-fixed text-xs">
        <thead>
          <tr className="bg-teal-50/80 text-teal-700">
            <th className={`px-3 py-2 text-left font-semibold ${COL_WIDTHS.param}`}>Param</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>Meas</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>Pred</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>LLN</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>ULN</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>% pred</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.num}`}>z</th>
            <th className={`px-3 py-2 text-right font-semibold ${COL_WIDTHS.status}`}>
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {spirometry.length > 0 && (
            <>
              <SectionHeader title="Spirometry" />
              {spirometry.map((r) => (
                <DataRow key={`s-${r.parameter}`} r={r} />
              ))}
            </>
          )}
          {lungVolumes.length > 0 && (
            <>
              <SectionHeader title="Lung volumes" />
              {lungVolumes.map((r) => (
                <DataRow key={`lv-${r.parameter}`} r={r} />
              ))}
            </>
          )}
        </tbody>
      </table>
    </div>
  )
}
