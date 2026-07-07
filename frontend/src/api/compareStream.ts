/**
 * Cliente SSE da comparacao com progresso real por etapa.
 */
import type {
  CompareCompleteEvent,
  CompareProgressState,
  CompareResponse,
  CompareStreamEvent,
  PipelineStep,
} from './types'
import { ApiError } from './client'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export interface CompareStreamResult {
  result: CompareResponse
  audit: PipelineStep[]
}

function parseSseLine(line: string): CompareStreamEvent | null {
  if (!line.startsWith('data: ')) {
    return null
  }
  try {
    return JSON.parse(line.slice(6)) as CompareStreamEvent
  } catch {
    return null
  }
}

export async function compareCircuitsStream(
  reference: File,
  test: File,
  options: {
    all?: boolean
    onProgress?: (progress: CompareProgressState) => void
  } = {},
): Promise<CompareStreamResult> {
  const formData = new FormData()
  formData.append('reference', reference)
  formData.append('test', test)

  const query = options.all ? '?all=true' : ''
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/compare/stream${query}`, {
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
    throw new ApiError(`Falha na requisicao (HTTP ${response.status}).`, response.status)
  }
  if (!response.body) {
    throw new ApiError('Resposta sem corpo do servidor.', response.status)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let complete: CompareCompleteEvent | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const event = parseSseLine(line.trim())
      if (!event) {
        continue
      }
      if (event.type === 'step') {
        options.onProgress?.({
          step: event.step,
          total: event.total,
          title: event.title,
          description: event.description,
          percent: event.percent,
          elapsedMs: event.elapsed_ms,
          etaMs: event.eta_ms,
          previewImage: event.image,
        })
      } else if (event.type === 'complete') {
        complete = event
        options.onProgress?.({
          step: 6,
          total: 6,
          title: 'Concluido',
          description: 'Comparacao finalizada.',
          percent: 100,
          elapsedMs: 0,
          etaMs: 0,
          previewImage: null,
        })
      } else if (event.type === 'error') {
        throw new ApiError(event.message, 422)
      }
    }
  }

  if (!complete) {
    throw new ApiError('Stream encerrado sem resultado final.', 0)
  }

  return { result: complete.result, audit: complete.audit }
}
