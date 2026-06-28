/**
 * Hook que encapsula a chamada de comparacao e seus estados (idle/loading/
 * success/error), mantendo os componentes focados em apresentacao.
 */
import { useCallback, useState } from 'react'

import { ApiError, compareCircuits } from '../api/client'
import type { CompareResponse } from '../api/types'

export type CompareStatus = 'idle' | 'loading' | 'success' | 'error'

interface CompareState {
  status: CompareStatus
  result: CompareResponse | null
  error: string | null
}

const INITIAL_STATE: CompareState = {
  status: 'idle',
  result: null,
  error: null,
}

export function useCompare() {
  const [state, setState] = useState<CompareState>(INITIAL_STATE)

  const compare = useCallback(async (reference: File, test: File) => {
    setState({ status: 'loading', result: null, error: null })
    try {
      const result = await compareCircuits(reference, test)
      setState({ status: 'success', result, error: null })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Erro inesperado ao comparar as imagens.'
      setState({ status: 'error', result: null, error: message })
    }
  }, [])

  const reset = useCallback(() => setState(INITIAL_STATE), [])

  return { ...state, compare, reset }
}
