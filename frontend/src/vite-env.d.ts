/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL da API. Vazio = usa o proxy do Vite (/api). */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
