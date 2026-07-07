import { describe, expect, it } from 'vitest'

import type { Box } from '../api/types'
import { boxCenter, labelAnchor, scaleBoxExact } from './overlayGeometry'

describe('overlayGeometry', () => {
  it('escala caixas sem inflar tamanho', () => {
    const box: Box = [100, 100, 108, 106]
    const scaled = scaleBoxExact(box, 200, 200, 100, 100)
    expect(scaled.width).toBe(4)
    expect(scaled.height).toBe(3)
  })

  it('calcula centro da caixa', () => {
    const center = boxCenter({ left: 10, top: 20, width: 20, height: 10 })
    expect(center).toEqual({ x: 20, y: 25 })
  })

  it('posiciona etiqueta acima quando houver espaco', () => {
    const anchor = labelAnchor(
      { left: 40, top: 60, width: 20, height: 20 },
      { width: 200, height: 200 },
    )
    expect(anchor.y).toBeLessThan(60)
  })
})
