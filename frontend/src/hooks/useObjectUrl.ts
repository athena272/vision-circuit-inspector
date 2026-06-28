/**
 * Cria uma object URL para um `File` e a revoga ao trocar/desmontar,
 * evitando vazamento de memoria.
 */
import { useEffect, useState } from 'react'

export function useObjectUrl(file: File | null): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setUrl(null)
      return
    }
    const objectUrl = URL.createObjectURL(file)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [file])

  return url
}
