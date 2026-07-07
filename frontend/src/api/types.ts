/**
 * Contratos da API, espelhando os DTOs do backend.
 */

export type Box = [number, number, number, number]
export type DifferenceKind = 'mismatched' | 'missing' | 'extra'

export interface Difference {
  kind: DifferenceKind
  label: string
  detail: string
  expected_box: Box | null
  actual_box: Box | null
  salience: number
}

export interface PipelineStep {
  id: number
  title: string
  description: string
  image_data_url: string
  duration_ms: number
}

export interface CompareResponse {
  is_match: boolean
  matched_count: number
  test_width: number
  test_height: number
  single_error_mode: boolean
  primary_difference: Difference | null
  differences: Difference[]
  all_differences: Difference[]
  audit: PipelineStep[]
}

export interface CompareStepEvent {
  type: 'step'
  step: number
  total: number
  title: string
  description: string
  percent: number
  elapsed_ms: number
  eta_ms: number | null
  image: string
}

export interface CompareCompleteEvent {
  type: 'complete'
  percent: number
  result: CompareResponse
  audit: PipelineStep[]
}

export interface CompareErrorEvent {
  type: 'error'
  message: string
}

export type CompareStreamEvent =
  | CompareStepEvent
  | CompareCompleteEvent
  | CompareErrorEvent

export interface CompareProgressState {
  step: number
  total: number
  title: string
  description: string
  percent: number
  elapsedMs: number
  etaMs: number | null
  previewImage: string | null
}
