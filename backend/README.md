# Circuit Inspector - Backend

Nucleo de visao computacional (OpenCV) e API HTTP (FastAPI) para comparar duas
fotos de circuitos em protoboard (gabarito vs aluno) e destacar as divergencias.

A documentacao completa do projeto (pipeline, modos de comparacao, CLI e detalhes
de arquitetura) esta no [README da raiz](../README.md).

## Desenvolvimento

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[api,dev]"
pytest
```

## Executar a API localmente

```bash
circuit-inspector-api            # http://127.0.0.1:8000
# ou:
uvicorn circuit_inspector.api.app:app --reload
```

Endpoints: `GET /api/health` e `POST /api/compare` (multipart com `reference` e
`test`). Detalhes do contrato no README da raiz.

## Deploy (Cloud Run via Cloud Build)

O `Dockerfile` empacota a API e o `cloudbuild.yaml` constroi a imagem, publica no
Artifact Registry e faz o deploy no Cloud Run. A imagem escuta em `0.0.0.0:$PORT`
(o Cloud Run injeta `PORT`, padrao `8080`).
