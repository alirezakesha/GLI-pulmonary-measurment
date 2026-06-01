export type Module = 'spirometry' | 'lung_volumes'

export interface MeasuredValues {
  FEV1?: number
  FVC?: number
  FEV1FVC?: number
  TLC?: number
  FRC?: number
  RV?: number
  RVTLC?: number
  ERV?: number
  IC?: number
  VC?: number
}

export interface ParameterResult {
  parameter: string
  full_name: string
  unit: string
  predicted: number
  lln: number
  uln: number
  lln_pct_pred: number
  measured?: number
  pct_pred?: number
  z_score?: number
  status?: 'below_lln' | 'above_uln' | 'normal' | null
}

export interface PatternClassification {
  pattern:
    | 'normal'
    | 'obstruction'
    | 'restriction'
    | 'mixed'
    | 'insufficient_data'
  label: string
  detail: string
  fev1fvc_below_lln?: boolean | null
  tlc_below_lln?: boolean | null
}

export interface ManualCalculateResponse {
  patient: {
    age: number
    height_cm: number
    sex: string
    modules: Module[]
    measured: Record<string, number>
  }
  spirometry: ParameterResult[]
  lung_volumes: ParameterResult[]
  classification?: PatternClassification | null
}

export interface FieldDefinition {
  key: string
  label: string
  group: 'demographics' | 'spirometry' | 'lung_volumes'
  required?: boolean
  unit?: string
  hint?: string
}

export type ColumnMapping = Record<string, string | null | undefined>

export interface BatchPreviewResponse {
  filename: string
  columns: string[]
  sample_rows: Record<string, unknown>[]
  row_count: number
  suggested_mapping: ColumnMapping
  available_fields: FieldDefinition[]
}

export interface BatchRowResult {
  row_index: number
  patient_id?: string
  age?: number
  sex?: string
  height_cm?: number
  spirometry: ParameterResult[]
  lung_volumes: ParameterResult[]
  classification?: PatternClassification | null
  errors: string[]
  flags: string[]
}

export interface BatchCalculateResponse {
  filename: string
  output_filename: string
  processed: number
  skipped: number
  results: BatchRowResult[]
  excel_base64: string
  added_columns: string[]
}
