import type { PatternClassification } from '../types'

const STYLES: Record<string, string> = {
  normal: 'bg-emerald-100 text-emerald-900 ring-emerald-200',
  obstruction: 'bg-amber-100 text-amber-900 ring-amber-200',
  restriction: 'bg-sky-100 text-sky-900 ring-sky-200',
  mixed: 'bg-violet-100 text-violet-900 ring-violet-200',
  insufficient_data: 'bg-slate-100 text-slate-700 ring-slate-200',
}

interface Props {
  classification: PatternClassification
  compact?: boolean
}

export function PatternClassificationCard({ classification, compact }: Props) {
  const style = STYLES[classification.pattern] ?? STYLES.insufficient_data

  if (compact) {
    return (
      <span
        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${style}`}
        title={classification.detail}
      >
        {classification.label}
      </span>
    )
  }

  return (
    <div className={`rounded-2xl px-5 py-4 ring-1 ring-inset ${style}`}>
      <p className="text-xs font-semibold uppercase tracking-wide opacity-80">
        PFT pattern (FEV₁/FVC + TLC vs LLN)
      </p>
      <p className="mt-1 font-display text-xl font-bold">{classification.label}</p>
      <p className="mt-2 text-sm leading-relaxed opacity-90">{classification.detail}</p>
      {(classification.fev1fvc_below_lln != null ||
        classification.tlc_below_lln != null) && (
        <ul className="mt-3 flex flex-wrap gap-3 text-xs">
          {classification.fev1fvc_below_lln != null && (
            <li>
              FEV₁/FVC:{' '}
              {classification.fev1fvc_below_lln ? 'below LLN' : '≥ LLN'}
            </li>
          )}
          {classification.tlc_below_lln != null && (
            <li>TLC: {classification.tlc_below_lln ? 'below LLN' : '≥ LLN'}</li>
          )}
        </ul>
      )}
    </div>
  )
}
