import { describe, expect, it } from 'vitest'

import type { Box } from '../api/types'
import { scaleBox } from './scaleBox'

describe('scaleBox', () => {
  it('mantem a caixa quando natural e renderizado coincidem', () => {
    const box: Box = [10, 20, 30, 50]

    expect(scaleBox(box, 100, 100, 100, 100)).toEqual({
      left: 10,
      top: 20,
      width: 20,
      height: 30,
    })
  })

  it('escala proporcionalmente quando a imagem e reduzida', () => {
    const box: Box = [20, 40, 60, 80]

    expect(scaleBox(box, 200, 200, 100, 100)).toEqual({
      left: 10,
      top: 20,
      width: 20,
      height: 20,
    })
  })

  it('normaliza coordenadas invertidas (x1 < x0)', () => {
    const box: Box = [30, 50, 10, 20]

    expect(scaleBox(box, 100, 100, 100, 100)).toEqual({
      left: 10,
      top: 20,
      width: 20,
      height: 30,
    })
  })

  it('satura caixas que ultrapassam a area renderizada', () => {
    const box: Box = [-10, -10, 150, 150]

    expect(scaleBox(box, 100, 100, 100, 100)).toEqual({
      left: 0,
      top: 0,
      width: 100,
      height: 100,
    })
  })

  it('retorna caixa vazia para dimensoes naturais invalidas', () => {
    const box: Box = [10, 10, 20, 20]

    expect(scaleBox(box, 0, 0, 100, 100)).toEqual({
      left: 0,
      top: 0,
      width: 0,
      height: 0,
    })
  })
})
