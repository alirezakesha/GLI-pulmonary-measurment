interface Props {
  status?: string | null
}

export function StatusBadge({ status }: Props) {
  if (!status) return <span className="text-slate-400">—</span>

  const styles: Record<string, string> = {
    normal: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    below_lln: 'bg-rose-100 text-rose-800 ring-rose-200',
    above_uln: 'bg-amber-100 text-amber-800 ring-amber-200',
  }

  const labels: Record<string, string> = {
    normal: 'Normal',
    below_lln: 'Below LLN',
    above_uln: 'Above ULN',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${styles[status] ?? 'bg-slate-100 text-slate-600'}`}
    >
      {labels[status] ?? status}
    </span>
  )
}
