# Imagem do backend (API FastAPI de visao computacional) para Cloud Run.
FROM python:3.12-slim

# Bibliotecas de sistema exigidas pelo OpenCV (opencv-python) para importar cv2.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Metadados + codigo-fonte: necessarios para o build do pacote (setuptools).
COPY pyproject.toml README.md ./
COPY src ./src

# Instala o pacote com as dependencias da API (fastapi, uvicorn, python-multipart).
RUN pip install --upgrade pip \
 && pip install ".[api]"

# Executa como usuario nao-root.
RUN useradd --create-home --uid 1000 appuser
USER appuser

# O Cloud Run injeta a variavel PORT (padrao 8080); o uvicorn precisa ouvir 0.0.0.0.
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn circuit_inspector.api.app:app --host 0.0.0.0 --port ${PORT}"]
