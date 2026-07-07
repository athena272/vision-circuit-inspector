/**
 * Geometria de overlays: escala e centro de caixas.
 */
import type { Box } from '../api/types'

import type { ScaledBox } from './scaleBox'
import { scaleBox } from './scaleBox'

export interface Point {
  x: number
  y: number
}

export function scaleBoxExact(
  box: Box,
  naturalWidth: number,
  naturalHeight: number,
  renderedWidth: number,
  renderedHeight: number,
): ScaledBox {
  return scaleBox(box, naturalWidth, naturalHeight, renderedWidth, renderedHeight)
}

export function boxCenter(box: ScaledBox): Point {
  return {
    x: box.left + box.width / 2,
    y: box.top + box.height / 2,
  }
}

export function boxFromCenter(center: Point, width: number, height: number): ScaledBox {
  return {
    left: center.x - width / 2,
    top: center.y - height / 2,
    width,
    height,
  }
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y)
}

/** Posiciona etiqueta fora da caixa, evitando bordas da imagem. */
export function labelAnchor(
  box: ScaledBox,
  rendered: { width: number; height: number },
): Point {
  const center = boxCenter(box)
  const above = box.top > 28
  const below = rendered.height - (box.top + box.height) > 28
  const y = above
    ? box.top - 10
    : below
      ? box.top + box.height + 18
      : center.y
  const x = Math.min(Math.max(center.x, 36), rendered.width - 36)
  return { x, y }
}
