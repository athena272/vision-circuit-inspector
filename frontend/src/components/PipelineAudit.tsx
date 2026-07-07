/**
 * Painel de auditoria das 6 etapas do pipeline de visao.
 */
import { useState } from 'react'

import type { PipelineStep } from '../api/types'

interface PipelineAuditProps {
  steps: PipelineStep[]
}

export function PipelineAudit({ steps }: PipelineAuditProps) {
  const [activeId, setActiveId] = useState(steps[0]?.id ?? 1)
  const active = steps.find((step) => step.id === activeId) ?? steps[0]

  if (!active || steps.length === 0) {
    return null
  }

  return (
    <section className="pipeline-audit">
      <h2>Auditoria do processamento</h2>
      <p className="pipeline-audit__intro">
        Veja o que o sistema fez em cada etapa, do upload ate a deteccao da
        divergencia.
      </p>

      <div className="pipeline-audit__layout">
        <ol className="pipeline-audit__steps">
          {steps.map((step) => (
            <li key={step.id}>
              <button
                type="button"
                className={
                  step.id === activeId
                    ? 'pipeline-audit__step pipeline-audit__step--active'
                    : 'pipeline-audit__step'
                }
                onClick={() => setActiveId(step.id)}
              >
                <span className="pipeline-audit__step-num">{step.id}</span>
                <span>{step.title}</span>
              </button>
            </li>
          ))}
        </ol>

        <div className="pipeline-audit__detail">
          <h3>{active.title}</h3>
          <p>{active.description}</p>
          <img
            src={active.image_data_url}
            alt={`Etapa ${active.id}: ${active.title}`}
          />
        </div>
      </div>
    </section>
  )
}
