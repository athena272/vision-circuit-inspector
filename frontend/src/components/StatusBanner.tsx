/**
 * Faixa de feedback do estado atual da comparacao.
 */
import type { CompareStatus } from '../hooks/useCompare'
import type { CompareResponse } from '../api/types'

interface StatusBannerProps {
  status: CompareStatus
  result: CompareResponse | null
  error: string | null
}

export function StatusBanner({ status, result, error }: StatusBannerProps) {
  if (status === 'loading') {
    return <div className="banner banner--info">Comparando imagens...</div>
  }

  if (status === 'error') {
    return <div className="banner banner--error">{error}</div>
  }

  if (status === 'success' && result) {
    if (result.is_match) {
      return (
        <div className="banner banner--success">
          Nenhuma divergencia detectada. O circuito confere com o gabarito.
        </div>
      )
    }
    const count = result.differences.length
    return (
      <div className="banner banner--warning">
        {count === 1
          ? '1 divergencia detectada.'
          : `${count} divergencias detectadas.`}
      </div>
    )
  }

  return null
}
