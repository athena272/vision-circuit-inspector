import { useState } from 'react'

import './App.css'
import { ImageInput } from './components/ImageInput'
import { ResultOverlay } from './components/ResultOverlay'
import { DifferenceList } from './components/DifferenceList'
import { StatusBanner } from './components/StatusBanner'
import { PipelineAudit } from './components/PipelineAudit'
import { useCompare } from './hooks/useCompare'
import { useObjectUrl } from './hooks/useObjectUrl'

function App() {
  const [reference, setReference] = useState<File | null>(null)
  const [test, setTest] = useState<File | null>(null)
  const {
    status,
    result,
    audit,
    error,
    progress,
    activeDifferences,
    compare,
    reset,
    toggleShowAll,
    showAllDifferences,
  } = useCompare()

  const testUrl = useObjectUrl(test)
  const canCompare = reference !== null && test !== null && status !== 'loading'
  const auditSteps = audit.length > 0 ? audit : (result?.audit ?? [])
  const hasMultiple =
    (result?.all_differences.length ?? 0) > 1 ||
    (result?.differences.length ?? 0) > 1

  const handleSelect = (setter: (file: File | null) => void) => (file: File | null) => {
    setter(file)
    if (status !== 'idle') {
      reset()
    }
  }

  const handleCompare = () => {
    if (reference && test) {
      void compare(reference, test)
    }
  }

  return (
    <main className="app">
      <header className="app__header">
        <h1>Circuit Inspector</h1>
        <p>
          Compare a foto do gabarito com a do circuito do aluno. O sistema mostra
          cada etapa do processamento e destaca a divergencia principal.
        </p>
      </header>

      <section className="inputs">
        <ImageInput
          id="reference"
          label="Gabarito"
          file={reference}
          onSelect={handleSelect(setReference)}
        />
        <ImageInput
          id="test"
          label="Circuito do aluno"
          file={test}
          onSelect={handleSelect(setTest)}
        />
      </section>

      <div className="actions">
        <button
          type="button"
          className="actions__compare"
          onClick={handleCompare}
          disabled={!canCompare}
        >
          {status === 'loading' ? 'Comparando...' : 'Comparar'}
        </button>
      </div>

      <StatusBanner
        status={status}
        result={result}
        error={error}
        progress={progress}
      />

      {status === 'success' && result && testUrl && (
        <>
          <section className="results">
            <ResultOverlay
              imageUrl={testUrl}
              differences={activeDifferences}
              naturalWidth={result.test_width}
              naturalHeight={result.test_height}
            />
            <div className="results__sidebar">
              <DifferenceList differences={activeDifferences} />
              {hasMultiple && (
                <button
                  type="button"
                  className="results__toggle"
                  onClick={toggleShowAll}
                >
                  {showAllDifferences
                    ? 'Mostrar apenas a divergencia principal'
                    : `Ver todas as divergencias (${result.all_differences.length})`}
                </button>
              )}
            </div>
          </section>
          {auditSteps.length > 0 && <PipelineAudit steps={auditSteps} />}
        </>
      )}
    </main>
  )
}

export default App
