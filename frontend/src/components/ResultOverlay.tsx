/**
 * Sobrepoe as caixas das diferencas a foto do aluno.
 *
 * Verde = posicao esperada (gabarito); vermelho = posicao atual (aluno).
 * As caixas sao escaladas das coordenadas naturais para o tamanho renderizado,
 * acompanhando o redimensionamento da imagem.
 */
import { useEffect, useRef, useState } from 'react'

import type { Difference } from '../api/types'
import { scaleBox } from '../utils/scaleBox'

interface ResultOverlayProps {
  imageUrl: string
  differences: Difference[]
  naturalWidth: number
  naturalHeight: number
}

interface Size {
  width: number
  height: number
}

export function ResultOverlay({
  imageUrl,
  differences,
  naturalWidth,
  naturalHeight,
}: ResultOverlayProps) {
  const imageRef = useRef<HTMLImageElement>(null)
  const rendered = useRenderedSize(imageRef)

  return (
    <div className="overlay">
      <img
        ref={imageRef}
        className="overlay__image"
        src={imageUrl}
        alt="Circuito do aluno com diferencas destacadas"
      />

      {rendered &&
        differences.map((difference, index) => (
          <DifferenceBoxes
            key={index}
            index={index}
            difference={difference}
            naturalWidth={naturalWidth}
            naturalHeight={naturalHeight}
            rendered={rendered}
          />
        ))}
    </div>
  )
}

interface DifferenceBoxesProps {
  index: number
  difference: Difference
  naturalWidth: number
  naturalHeight: number
  rendered: Size
}

function DifferenceBoxes({
  index,
  difference,
  naturalWidth,
  naturalHeight,
  rendered,
}: DifferenceBoxesProps) {
  const marker = index + 1
  return (
    <>
      {difference.expected_box && (
        <Marker
          variant="expected"
          label={`${marker} esperado`}
          box={scaleBox(
            difference.expected_box,
            naturalWidth,
            naturalHeight,
            rendered.width,
            rendered.height,
          )}
        />
      )}
      {difference.actual_box && (
        <Marker
          variant="actual"
          label={`${marker} atual`}
          box={scaleBox(
            difference.actual_box,
            naturalWidth,
            naturalHeight,
            rendered.width,
            rendered.height,
          )}
        />
      )}
    </>
  )
}

interface MarkerProps {
  variant: 'expected' | 'actual'
  label: string
  box: { left: number; top: number; width: number; height: number }
}

function Marker({ variant, label, box }: MarkerProps) {
  return (
    <div
      className={`marker marker--${variant}`}
      style={{
        left: `${box.left}px`,
        top: `${box.top}px`,
        width: `${box.width}px`,
        height: `${box.height}px`,
      }}
    >
      <span className="marker__label">{label}</span>
    </div>
  )
}

/** Observa o tamanho renderizado do elemento (responsivo). */
function useRenderedSize(ref: React.RefObject<HTMLElement | null>): Size | null {
  const [size, setSize] = useState<Size | null>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) {
      return
    }

    const update = () =>
      setSize({ width: element.clientWidth, height: element.clientHeight })

    update()
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref])

  return size
}
