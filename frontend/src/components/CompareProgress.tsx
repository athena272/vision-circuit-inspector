/**
 * Barra de progresso com etapa atual, percentual e tempo estimado.
 */
import type { CompareProgressState } from '../api/types'

interface CompareProgressProps {
  progress: CompareProgressState
}

function formatEta(ms: number | null): string {
  if (ms === null || ms <= 0) {
    return 'calculando...'
  }
  const seconds = Math.ceil(ms / 1000)
  if (seconds < 60) {
    return `~${seconds}s restantes`
  }
  const minutes = Math.ceil(seconds / 60)
  return `~${minutes} min restantes`
}

export function CompareProgress({ progress }: CompareProgressProps) {
  return (
    <div className="compare-progress">
      <div className="compare-progress__header">
        <span>
          Etapa {progress.step} de {progress.total} — {progress.title}
        </span>
        <span>{progress.percent}%</span>
      </div>
      <div className="compare-progress__bar" aria-hidden="true">
        <div
          className="compare-progress__fill"
          style={{ width: `${progress.percent}%` }}
        />
      </div>
      <p className="compare-progress__description">{progress.description}</p>
      <p className="compare-progress__eta">{formatEta(progress.etaMs)}</p>
      {progress.previewImage && (
        <img
          className="compare-progress__preview"
          src={progress.previewImage}
          alt={`Preview da etapa ${progress.title}`}
        />
      )}
    </div>
  )
}
