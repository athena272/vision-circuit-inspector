/**
 * Faixa de feedback do estado atual da comparacao.
 */
import type { CompareProgressState, CompareResponse } from '../api/types'
import type { CompareStatus } from '../hooks/useCompare'
import { CompareProgress } from './CompareProgress'

interface StatusBannerProps {
  status: CompareStatus
  result: CompareResponse | null
  error: string | null
  progress: CompareProgressState | null
}

export function StatusBanner({ status, result, error, progress }: StatusBannerProps) {
  if (status === 'loading' && progress) {
    return <CompareProgress progress={progress} />
  }

  if (status === 'loading') {
    return <div className="banner banner--info">Iniciando comparacao...</div>
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
    return (
      <div className="banner banner--warning">
        Divergencia principal detectada. Confira o destaque na imagem e a auditoria
        abaixo.
      </div>
    )
  }

  return null
}
