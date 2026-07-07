/**
 * Hook de comparacao com progresso real via SSE.
 */
import { useCallback, useState } from 'react'

import { ApiError } from '../api/client'
import { compareCircuitsStream } from '../api/compareStream'
import type { CompareProgressState, CompareResponse, PipelineStep } from '../api/types'

export type CompareStatus = 'idle' | 'loading' | 'success' | 'error'

interface CompareState {
  status: CompareStatus
  result: CompareResponse | null
  audit: PipelineStep[]
  error: string | null
  progress: CompareProgressState | null
  showAllDifferences: boolean
}

const INITIAL_STATE: CompareState = {
  status: 'idle',
  result: null,
  audit: [],
  error: null,
  progress: null,
  showAllDifferences: false,
}

export function useCompare() {
  const [state, setState] = useState<CompareState>(INITIAL_STATE)

  const compare = useCallback(async (reference: File, test: File) => {
    setState({
      status: 'loading',
      result: null,
      audit: [],
      error: null,
      progress: null,
      showAllDifferences: false,
    })
    try {
      const { result, audit } = await compareCircuitsStream(reference, test, {
        onProgress: (progress) => {
          setState((prev) => ({ ...prev, progress }))
        },
      })
      setState({
        status: 'success',
        result,
        audit,
        error: null,
        progress: null,
        showAllDifferences: false,
      })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Erro inesperado ao comparar as imagens.'
      setState({
        status: 'error',
        result: null,
        audit: [],
        error: message,
        progress: null,
        showAllDifferences: false,
      })
    }
  }, [])

  const reset = useCallback(() => setState(INITIAL_STATE), [])

  const toggleShowAll = useCallback(() => {
    setState((prev) => ({ ...prev, showAllDifferences: !prev.showAllDifferences }))
  }, [])

  const activeDifferences = (() => {
    if (!state.result) {
      return []
    }
    if (state.showAllDifferences && state.result.all_differences.length > 0) {
      return state.result.all_differences
    }
    if (state.result.primary_difference) {
      return [state.result.primary_difference]
    }
    return state.result.differences
  })()

  return {
    ...state,
    activeDifferences,
    compare,
    reset,
    toggleShowAll,
  }
}
