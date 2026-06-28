import { useState } from 'react'

import './App.css'
import { ImageInput } from './components/ImageInput'
import { ResultOverlay } from './components/ResultOverlay'
import { DifferenceList } from './components/DifferenceList'
import { StatusBanner } from './components/StatusBanner'
import { useCompare } from './hooks/useCompare'
import { useObjectUrl } from './hooks/useObjectUrl'

function App() {
  const [reference, setReference] = useState<File | null>(null)
  const [test, setTest] = useState<File | null>(null)
  const { status, result, error, compare, reset } = useCompare()

  const testUrl = useObjectUrl(test)
  const canCompare = reference !== null && test !== null && status !== 'loading'

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
          Compare a foto do gabarito com a do circuito do aluno e veja as
          divergencias destacadas automaticamente.
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

      <StatusBanner status={status} result={result} error={error} />

      {status === 'success' && result && testUrl && (
        <section className="results">
          <ResultOverlay
            imageUrl={testUrl}
            differences={result.differences}
            naturalWidth={result.test_width}
            naturalHeight={result.test_height}
          />
          <DifferenceList differences={result.differences} />
        </section>
      )}
    </main>
  )
}

export default App
