/**
 * Conversao de caixas das coordenadas naturais da imagem para o tamanho
 * renderizado na tela. Funcao pura, sem dependencia de DOM (testavel).
 */
import type { Box } from '../api/types'

export interface ScaledBox {
  left: number
  top: number
  width: number
  height: number
}

/**
 * Escala uma `Box` ([x0,y0,x1,y1]) das dimensoes naturais para as renderizadas.
 * Caixas sao saturadas a area visivel para nao vazarem da imagem.
 */
export function scaleBox(
  box: Box,
  naturalWidth: number,
  naturalHeight: number,
  renderedWidth: number,
  renderedHeight: number,
): ScaledBox {
  if (naturalWidth <= 0 || naturalHeight <= 0) {
    return { left: 0, top: 0, width: 0, height: 0 }
  }

  const scaleX = renderedWidth / naturalWidth
  const scaleY = renderedHeight / naturalHeight

  const [x0, y0, x1, y1] = box
  const left = clamp(Math.min(x0, x1) * scaleX, 0, renderedWidth)
  const top = clamp(Math.min(y0, y1) * scaleY, 0, renderedHeight)
  const right = clamp(Math.max(x0, x1) * scaleX, 0, renderedWidth)
  const bottom = clamp(Math.max(y0, y1) * scaleY, 0, renderedHeight)

  return { left, top, width: right - left, height: bottom - top }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}
