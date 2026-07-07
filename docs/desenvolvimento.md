# Desenvolvimento

Guia para quem vai rodar, testar ou estender o projeto localmente.

## Instalacao

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[api,dev]"
```

## CLI

```bash
circuit-inspector GABARITO.png ALUNO.png -o saida_anotada.png
```

Modos:

| Modo | Flag | Quando usar |
|------|------|-------------|
| Registro automatico (padrao) | — | Fotos reais, zero clique |
| Estrutural por furo | `--grid` | Com calibracao JSON |
| Por tipo de componente | `--typed` | Quando precisa nomear cada peca |

Use `--all` para listar todas as divergencias (em vez de uma so).

## API

```bash
circuit-inspector-api
# ou: uvicorn circuit_inspector.api.app:app --reload
```

Endpoints:

- `GET /api/health`
- `POST /api/compare` — sincrono; `?all=true` para todas as divergencias; `?include_audit=true` para as 6 imagens
- `POST /api/compare/stream` — SSE com progresso por etapa (usado pela SPA)

## Componentes suportados (modo `--typed`)

| Tipo | Detalhe |
|------|---------|
| Jumper | vermelho, laranja, verde, preto |
| LED | `led:blue`, `led:red` |
| LDR | corpo cinza |
| Resistor | filme metalico |
| Capacitor | corpo escuro, redondo |
| Potenciometro | corpo metalico |
| Push button | corpo escuro, quadrado |

## Calibrador interativo

Para fotos onde a malha automatica falha:

```bash
circuit-inspector-calibrate FOTO.png calib.json --holes 45:j 60:j 45:a 60:a
```

Teclas: `u` desfaz, `r` reinicia, `ESC` cancela.

Formato JSON (exemplo):

```json
{
  "correspondences": [
    {"hole": {"column": 45, "row": "j"}, "pixel": {"x": 120, "y": 210}},
    {"hole": {"column": 60, "row": "j"}, "pixel": {"x": 760, "y": 205}}
  ]
}
```

## Testes

```bash
cd backend
pytest                        # todos
pytest -m "not integration"   # unitarios
```

```bash
cd frontend
pnpm test
pnpm build
```

## Deploy

- **Backend:** Cloud Build + Cloud Run (`backend/cloudbuild.yaml`)
- **Frontend:** Vercel, root `frontend/`, `VITE_API_BASE_URL` apontando para a API

CORS no Cloud Run: `CIRCUIT_INSPECTOR_CORS_ORIGINS=https://vision-circuit-inspector.vercel.app`

## Ajuste fino

Parametros de ocupacao e ruido em `backend/src/circuit_inspector/config.py`
(`OccupancyConfig`): `alignment_dilate_kernel`, `pair_max_distance_frac`,
`min_salience_ratio`, `merge_cluster_distance_px`.
