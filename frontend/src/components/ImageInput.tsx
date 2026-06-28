/**
 * Seletor de imagem com preview, reutilizado para gabarito e aluno.
 */
import { useObjectUrl } from '../hooks/useObjectUrl'

interface ImageInputProps {
  id: string
  label: string
  file: File | null
  onSelect: (file: File | null) => void
}

export function ImageInput({ id, label, file, onSelect }: ImageInputProps) {
  const previewUrl = useObjectUrl(file)

  return (
    <div className="image-input">
      <label className="image-input__label" htmlFor={id}>
        {label}
      </label>

      <div className="image-input__drop">
        {previewUrl ? (
          <img className="image-input__preview" src={previewUrl} alt={label} />
        ) : (
          <span className="image-input__placeholder">Selecione uma imagem</span>
        )}
      </div>

      <input
        id={id}
        className="image-input__file"
        type="file"
        accept="image/*"
        onChange={(event) => onSelect(event.target.files?.[0] ?? null)}
      />
    </div>
  )
}
