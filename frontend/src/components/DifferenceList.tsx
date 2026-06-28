/**
 * Lista textual das diferencas detectadas, numerada de acordo com o overlay.
 */
import type { Difference, DifferenceKind } from '../api/types'

interface DifferenceListProps {
  differences: Difference[]
}

const KIND_LABEL: Record<DifferenceKind, string> = {
  mismatched: 'Movido',
  missing: 'Faltando',
  extra: 'Sobrando',
}

export function DifferenceList({ differences }: DifferenceListProps) {
  if (differences.length === 0) {
    return null
  }

  return (
    <ol className="difference-list">
      {differences.map((difference, index) => (
        <li className="difference-list__item" key={index}>
          <span className="difference-list__index">{index + 1}</span>
          <div className="difference-list__body">
            <span className={`badge badge--${difference.kind}`}>
              {KIND_LABEL[difference.kind]}
            </span>
            <span className="difference-list__label">{difference.label}</span>
            <p className="difference-list__detail">{difference.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}
