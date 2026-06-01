/** Aligned measurement inputs — same 3-column grid for spirometry and lung volumes. */

interface Field {
  key: string
  label: string
  unit: string
}

interface Props {
  fields: readonly Field[]
  values: Record<string, string>
  onChange: (key: string, value: string) => void
  inputClassName?: string
}

export function MeasurementGrid({
  fields,
  values,
  onChange,
  inputClassName = 'border-teal-100 focus:border-teal-400 focus:ring-teal-200',
}: Props) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {fields.map(({ key, label, unit }) => (
        <label key={key} className="flex min-h-[4.5rem] flex-col">
          <span className="text-xs font-medium leading-tight text-teal-700">
            {label}
            <span className="mt-0.5 block font-normal text-teal-500">({unit})</span>
          </span>
          <input
            type="number"
            step="any"
            value={values[key] ?? ''}
            onChange={(e) => onChange(key, e.target.value)}
            className={`mt-auto w-full rounded-lg border bg-white px-3 py-2 text-sm outline-none focus:ring-1 ${inputClassName}`}
          />
        </label>
      ))}
    </div>
  )
}
