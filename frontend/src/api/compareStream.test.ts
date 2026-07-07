import { describe, expect, it } from 'vitest'

function parseSseLine(line: string) {
  if (!line.startsWith('data: ')) {
    return null
  }
  return JSON.parse(line.slice(6))
}

describe('parseSseLine', () => {
  it('ignora linhas que nao sao eventos SSE', () => {
    expect(parseSseLine('')).toBeNull()
    expect(parseSseLine(': keepalive')).toBeNull()
  })

  it('parseia evento step', () => {
    const event = parseSseLine(
      'data: {"type":"step","step":2,"total":6,"percent":33}',
    )
    expect(event.type).toBe('step')
    expect(event.step).toBe(2)
  })
})
