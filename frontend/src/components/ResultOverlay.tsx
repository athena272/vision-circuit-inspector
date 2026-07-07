/**
 * Destaque visual das divergencias sobre a foto do aluno (SVG unico).
 *
 * Verde = gabarito; vermelho = aluno. Uma etiqueta por divergencia.
 */
import { useEffect, useRef, useState } from 'react'

import type { Difference } from '../api/types'
import {
  boxCenter,
  boxFromCenter,
  distance,
  labelAnchor,
  scaleBoxExact,
  type Point,
} from '../utils/overlayGeometry'

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

const COMPACT_DISTANCE_PX = 90

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

      {rendered && (
        <svg
          className="overlay__svg"
          width={rendered.width}
          height={rendered.height}
          aria-hidden
        >
          <defs>
            <marker
              id="overlay-arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="8"
              refY="5"
              orient="auto"
            >
              <path className="overlay__arrow-head" d="M0,0 L10,5 L0,10 Z" />
            </marker>
          </defs>

          {differences.map((difference, index) => (
            <DifferenceHighlight
              key={`${difference.kind}-${difference.label}-${index}`}
              index={index}
              difference={difference}
              naturalWidth={naturalWidth}
              naturalHeight={naturalHeight}
              rendered={rendered}
            />
          ))}
        </svg>
      )}
    </div>
  )
}

interface DifferenceHighlightProps {
  index: number
  difference: Difference
  naturalWidth: number
  naturalHeight: number
  rendered: Size
}

function DifferenceHighlight({
  index,
  difference,
  naturalWidth,
  naturalHeight,
  rendered,
}: DifferenceHighlightProps) {
  const expected = difference.expected_box
    ? scaleBoxExact(
        difference.expected_box,
        naturalWidth,
        naturalHeight,
        rendered.width,
        rendered.height,
      )
    : null
  const actual = difference.actual_box
    ? scaleBoxExact(
        difference.actual_box,
        naturalWidth,
        naturalHeight,
        rendered.width,
        rendered.height,
      )
    : null

  if (difference.kind === 'mismatched' && expected && actual) {
    const from = boxCenter(expected)
    const to = boxCenter(actual)
    const compact = distance(from, to) < COMPACT_DISTANCE_PX
    const badge = labelFor(difference, index + 1)
    const badgePos = compact
      ? offsetFromMidpoint(from, to, rendered)
      : labelAnchor(actual, rendered)

    return (
      <g className="overlay__group">
        {compact ? (
          <>
            <circle
              className="overlay__ring overlay__ring--expected"
              cx={from.x}
              cy={from.y}
              r={ringRadius(expected)}
            />
            <circle
              className="overlay__ring overlay__ring--actual"
              cx={to.x}
              cy={to.y}
              r={ringRadius(actual)}
            />
          </>
        ) : (
          <>
            <rect className="overlay__rect overlay__rect--expected" {...rectProps(expected)} />
            <rect className="overlay__rect overlay__rect--actual" {...rectProps(actual)} />
          </>
        )}
        <line
          className="overlay__arrow-line"
          x1={from.x}
          y1={from.y}
          x2={to.x}
          y2={to.y}
          markerEnd="url(#overlay-arrowhead)"
        />
        <Badge x={badgePos.x} y={badgePos.y} text={badge} />
      </g>
    )
  }

  const target = actual ?? expected
  if (!target) {
    return null
  }

  const variant = actual ? 'actual' : 'expected'
  const badgePos = labelAnchor(target, rendered)

  return (
    <g className="overlay__group">
      <rect
        className={`overlay__rect overlay__rect--${variant}`}
        {...rectProps(target)}
      />
      <Badge x={badgePos.x} y={badgePos.y} text={labelFor(difference, index + 1)} />
    </g>
  )
}

function rectProps(box: { left: number; top: number; width: number; height: number }) {
  return {
    x: box.left,
    y: box.top,
    width: Math.max(box.width, 4),
    height: Math.max(box.height, 4),
    rx: 6,
    ry: 6,
  }
}

function ringRadius(box: { width: number; height: number }): number {
  return Math.max(18, Math.max(box.width, box.height) * 0.55)
}

function offsetFromMidpoint(from: Point, to: Point, rendered: Size): Point {
  const mid = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 }
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const nx = -dy / len
  const ny = dx / len
  const candidate = { x: mid.x + nx * 34, y: mid.y + ny * 34 }
  return {
    x: Math.min(Math.max(candidate.x, 40), rendered.width - 40),
    y: Math.min(Math.max(candidate.y, 24), rendered.height - 16),
  }
}

function labelFor(difference: Difference, index: number): string {
  const kind =
    difference.kind === 'mismatched'
      ? 'movido'
      : difference.kind === 'extra'
        ? 'sobrando'
        : 'faltando'
  return `${index} · ${kind}`
}

interface BadgeProps {
  x: number
  y: number
  text: string
}

function Badge({ x, y, text }: BadgeProps) {
  const width = Math.max(58, text.length * 6.8 + 18)
  const height = 22
  const box = boxFromCenter({ x, y }, width, height)
  return (
    <g className="overlay__badge">
      <rect
        x={box.left}
        y={box.top}
        width={box.width}
        height={box.height}
        rx={5}
        ry={5}
      />
      <text x={x} y={y + 4} textAnchor="middle">
        {text}
      </text>
    </g>
  )
}

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
