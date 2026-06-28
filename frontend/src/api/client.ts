/**
 * Cliente HTTP da API de inspecao.
 *
 * Centraliza o acesso a rede: monta o request, trata erros e devolve dados
 * fortemente tipados, isolando os componentes de detalhes de transporte.
 */
import type { CompareResponse } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Erro de API com a mensagem amigavel vinda do backend e o status HTTP. */
export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // Resposta sem corpo JSON; cai no fallback abaixo.
  }
  return `Falha na requisicao (HTTP ${response.status}).`
}

/**
 * Compara duas fotos de circuito (gabarito x aluno) e devolve as diferencas.
 *
 * @throws {ApiError} quando o backend rejeita ou falha na requisicao.
 */
export async function compareCircuits(
  reference: File,
  test: File,
): Promise<CompareResponse> {
  const formData = new FormData()
  formData.append('reference', reference)
  formData.append('test', test)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/compare`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new ApiError(
      'Nao foi possivel conectar a API. Verifique se o backend esta no ar.',
      0,
    )
  }

  if (!response.ok) {
    throw new ApiError(await extractErrorMessage(response), response.status)
  }

  return (await response.json()) as CompareResponse
}
