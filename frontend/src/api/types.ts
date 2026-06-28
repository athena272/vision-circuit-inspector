/**
 * Contratos da API, espelhando os DTOs do backend (`circuit_inspector.api.schemas`).
 */

/** Caixa em pixels da imagem do aluno: [x0, y0, x1, y1]. */
export type Box = [number, number, number, number]

/** Natureza de uma diferenca detectada. */
export type DifferenceKind = 'mismatched' | 'missing' | 'extra'

export interface Difference {
  kind: DifferenceKind
  label: string
  detail: string
  /** Posicao no gabarito (verde), quando aplicavel. */
  expected_box: Box | null
  /** Posicao no aluno (vermelho), quando aplicavel. */
  actual_box: Box | null
  salience: number
}

export interface CompareResponse {
  is_match: boolean
  matched_count: number
  test_width: number
  test_height: number
  differences: Difference[]
}
