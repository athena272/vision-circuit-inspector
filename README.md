# vision-circuit-inspector

Nucleo de **visao computacional (OpenCV classico)** para comparar duas fotos
top-down de circuitos em protoboard - um **gabarito** e o **circuito do aluno** -
identificar componentes posicionados em **terminais errados** e gerar uma
**imagem anotada** destacando as divergencias.

## Problema

Dado um par de imagens de circuitos simples em protoboard, detectar qual
componente esta em um furo `(coluna, linha)` diferente do gabarito e destaca-lo -
como uma marcacao manual feita a mao.

Componentes suportados:

| Tipo | Detalhe |
|------|---------|
| Jumper (fio) | cores: vermelho, laranja, verde, preto |
| LED | por cor: `led:blue`, `led:red` (cores diferentes = componentes diferentes) |
| LDR | corpo cinza compacto |
| Resistor | corpo de filme metalico, alongado |
| Capacitor eletrolitico | corpo escuro, redondo, grande |
| Potenciometro | corpo metalico grande |
| Push button | corpo escuro, quadrado |

## Pipeline

```
gabarito ─┐
          ├─> retificacao + malha ─> deteccao ─> mapeia furos ─┐
aluno   ──┘                                                    ├─> comparador ─> anotacao + relatorio
```

1. **Retificacao + malha** (`board/`): detecta a malha de furos e estima uma
   homografia que leva as coordenadas canonicas do board para os pixels da foto.
   As duas imagens compartilham o mesmo sistema canonico, de modo que
   `(coluna, linha)` identifica o mesmo ponto fisico nas duas.
2. **Deteccao** (`detection/`): cada componente tem um detector (padrao
   Strategy) baseado em cor (HSV) e forma. Jumpers e resistores sao blobs
   alongados; LED, LDR, capacitor e potenciometro sao blobs compactos
   (separados por cor/area/circularidade); o push button e um blob escuro
   quadrado. Adicionar um novo tipo e so criar um detector e registra-lo no
   `registry` (Open/Closed), sem tocar no pipeline.
3. **Mapeamento** (`mapping.py`): associa cada terminal (pixel) ao furo mais
   proximo, produzindo um `Placement`.
4. **Comparacao** (`comparison/`): casa componentes por tipo/cor e gera
   divergencias: em furo errado (mismatched), faltando (missing) ou sobrando
   (extra).
5. **Anotacao** (`visualization/`): desenha caixas vermelhas (errado/sobrando) e
   verdes (posicao esperada) na imagem do aluno.

## Estrutura (monorepo)

```
backend/                     # nucleo de visao + API (Python)
  pyproject.toml
  src/circuit_inspector/
    config.py                # geometria do board, faixas HSV, tolerancias
    models.py                # dataclasses do dominio
    pipeline.py              # orquestracao ponta a ponta
    cli.py                   # interface de linha de comando
    io/image_loader.py
    board/                   # hole_detector, rectifier, grid_mapper, registration
    detection/               # base + detectores + registry
    comparison/              # comparator + structural + registered + report + selection
    visualization/annotator.py
    tools/calibrate.py       # calibrador interativo (clicar furos -> JSON)
    api/                     # FastAPI: app + schemas + mappers
  tests/
    unit/                    # testes deterministicos
    integration/             # pipeline + API ponta a ponta
    fixtures/synthetic_board.py
  assets/                    # imagens de exemplo
frontend/                    # SPA React + Vite (TypeScript)
  src/
    api/                     # client HTTP tipado + tipos dos DTOs
    components/              # ImageInput, ResultOverlay, DifferenceList, StatusBanner
    hooks/                   # useCompare, useObjectUrl
    utils/scaleBox.ts        # escala de caixas natural -> render (testada)
    App.tsx
```

## Instalacao

Requer Python 3.10+. Trabalhe a partir de `backend/`:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[api,dev]"     # api = FastAPI/uvicorn; dev = pytest/httpx
```

## Uso (CLI)

```bash
circuit-inspector GABARITO.png ALUNO.png -o saida_anotada.png
```

Por padrao usa o **registro automatico** (alinha as duas fotos sozinho, **sem
nenhum clique/calibracao**) e assume **um erro por placa**, destacando apenas a
divergencia mais relevante (vermelho = posicao no aluno, verde = posicao no
gabarito). Use `--all` para listar/anotar todas as divergencias.

Modos alternativos (exigem calibracao da malha): `--grid` (estrutural por
ocupacao de furo) e `--typed` (deteccao por cor/forma).

Para fotos com varias secoes de protoboard (onde a estimativa automatica da
malha falha), use **calibracao assistida**:

```bash
circuit-inspector GABARITO.png ALUNO.png --calibration calib.json -o saida.png
# ou, se o enquadramento difere entre as fotos:
circuit-inspector GABARITO.png ALUNO.png \
    --reference-calibration calib_gabarito.json \
    --test-calibration calib_aluno.json
```

Codigos de saida: `0` equivalentes, `1` divergencias, `2` erro.

### Formato do JSON de calibracao

Informe ao menos 4 furos conhecidos com seus pixels (cantos da secao principal):

```json
{
  "correspondences": [
    {"hole": {"column": 45, "row": "j"}, "pixel": {"x": 120, "y": 210}},
    {"hole": {"column": 60, "row": "j"}, "pixel": {"x": 760, "y": 205}},
    {"hole": {"column": 45, "row": "a"}, "pixel": {"x": 118, "y": 560}},
    {"hole": {"column": 60, "row": "a"}, "pixel": {"x": 758, "y": 555}}
  ]
}
```

### Calibrador interativo (gera o JSON clicando)

Em vez de medir os pixels a mao, use o calibrador: ele abre a foto, voce clica
nos furos de referencia (na ordem) e ele salva o JSON. Ao final, mostra a malha
estimada sobre a imagem para conferencia.

```bash
circuit-inspector-calibrate FOTO.png calib.json --holes 45:j 60:j 45:a 60:a
# (sem instalar o entry point: python -m circuit_inspector.tools.calibrate ...)
```

- Cada furo e `coluna:linha` (ex.: `45:j`) ou `coluna:trilha` (ex.: `60:+`).
- Clique exatamente sobre o centro de cada furo, na ordem listada em `--holes`.
- Teclas na janela: `ESC` cancela, `u`/Backspace desfaz o ultimo clique, `r`
  reinicia. A janela e redimensionavel (`WINDOW_NORMAL`) para dar zoom.
- Faca **uma calibracao por foto** quando o enquadramento difere entre gabarito
  e aluno, e passe cada JSON em `--reference-calibration` / `--test-calibration`.
- Mais furos (alem de 4) tornam a homografia mais robusta a distorcoes.

### Modos de comparacao

- **Registro automatico (padrao):** alinha a foto do aluno sobre a do gabarito
  estimando uma homografia por casamento de features (SIFT + RANSAC) — sem
  cliques nem calibracao. Como a maior parte da placa e identica, sobram muitas
  correspondencias e o(s) componente(s) movido(s) viram outliers. No frame
  alinhado, compara a *ocupacao* (saturacao) e destaca a regiao que mudou.
  Elimina a inconsistencia de calibrar duas fotos a mao (a maior fonte de
  ruido). Rotulos sao por *cor* da regiao (ex.: "componente azul"), nao pela
  serigrafia.
- **Estrutural por ocupacao de furo (`--grid`):** mede a saturacao por furo e
  compara a ocupacao entre as duas malhas calibradas. Tipo-agnostico; requer
  calibracao (`--calibration`/`--*-calibration`). Veja `OccupancyConfig`.
- **Por tipo (`--typed`):** detectores por cor/forma (padrao Strategy); requer
  malha (calibracao). Util quando se quer nomear cada componente.

Limitacao comum aos modos por ocupacao: cobrem componentes *coloridos*
(resistor, LED, jumpers); corpos de baixa saturacao (LDR cinza, fio preto) nao
entram. O registro automatico assume que ambas as fotos mostram a mesma placa de
forma nitida e com enquadramento parecido.

## Uso programatico

```python
from circuit_inspector.pipeline import inspect

result = inspect("gabarito.png", "aluno.png")
print(result.comparison.is_match)
for diff in result.comparison.differences:
    print(diff.kind.value, diff.detail)
```

### Calibracao assistida (recomendado para fotos reais)

A estimativa automatica da malha funciona bem em fotos top-down de uma unica
protoboard. Quando o enquadramento inclui mais de uma secao de board ou ha
distorcao, use a calibracao informando 4 (ou mais) furos de referencia
conhecidos:

```python
from circuit_inspector.board.rectifier import GridCalibration
from circuit_inspector.models import Hole, Point
from circuit_inspector.pipeline import inspect

calib = GridCalibration(correspondences=(
    (Hole(50, row="j"), Point(x=410, y=200)),
    (Hole(60, row="j"), Point(x=770, y=200)),
    (Hole(50, row="a"), Point(x=410, y=540)),
    (Hole(60, row="a"), Point(x=770, y=540)),
))
result = inspect("gabarito.png", "aluno.png",
                 reference_calibration=calib, test_calibration=calib)
```

## API (FastAPI) e Frontend (React)

A fatia web usa o **modo de registro automatico** (zero clique). O backend expoe
uma API fina e o frontend faz upload do par e desenha as diferencas sobre a foto
do aluno.

### Backend (API)

```bash
cd backend
.venv\Scripts\activate
circuit-inspector-api            # sobe em http://127.0.0.1:8000
# alternativa: uvicorn circuit_inspector.api.app:app --reload
```

Endpoints:

- `GET /api/health` — checagem simples (`{"status": "ok"}`).
- `POST /api/compare` — `multipart/form-data` com os campos `reference` e `test`
  (imagens). Retorna JSON `{ is_match, matched_count, test_width, test_height,
  differences[] }`, onde cada diferenca traz `kind` (`mismatched`/`missing`/
  `extra`), `label`, `detail`, `expected_box` (gabarito) e `actual_box` (aluno)
  em pixels da foto do aluno.

CORS libera `http://localhost:5173` por padrao (sobrescrevivel via
`CIRCUIT_INSPECTOR_CORS_ORIGINS`, lista separada por virgula).

### Frontend (SPA)

```bash
cd frontend
pnpm install
pnpm dev                         # http://localhost:5173
```

Em dev, o Vite faz proxy de `/api` para `http://localhost:8000` (veja
`vite.config.ts`), entao basta ter o backend no ar. Para apontar para outra API,
defina `VITE_API_BASE_URL` em `frontend/.env`.

## Testes

Backend (a partir de `backend/`):

```bash
pytest                        # todos
pytest -m "not integration"   # apenas unitarios
```

Frontend (a partir de `frontend/`):

```bash
pnpm test                     # vitest (funcoes puras, ex.: scaleBox)
```

Os testes unitarios sao deterministicos (geometria, comparacao, detectores sobre
imagens sinteticas). A integracao cobre o pipeline ponta a ponta com uma
protoboard sintetica (assercoes exatas) e um smoke test sobre fotos reais.

## Limitacoes conhecidas e ajuste fino

- **Registro automatico (padrao)** assume fotos nitidas da mesma placa e
  enquadramento parecido; se o casamento de features falhar, ele avisa e voce
  pode cair para `--grid` com calibracao.
- **Modos `--grid`/`--typed` exigem calibracao consistente**: como gabarito e
  aluno sao fotos separadas, cada uma tem sua malha; se os pontos clicados nao
  forem precisos, as duas malhas discordam em ~1 furo e deslocamentos pequenos se
  confundem com o ruido. (O registro automatico evita esse problema.)
- **Modos por ocupacao cobrem componentes coloridos**: LDR cinza e fio preto tem
  baixa saturacao e nao entram; use `--typed` se o erro envolver esses
  componentes.
- **Um erro por placa**: o destaque assume um unico componente movido. Se varios
  se moverem entre as fotos, o modo padrao mostra o mais saliente (use `--all`).
- **Deteccao por cor exige tuning**: as faixas HSV em `config.py`
  (`ColorProfiles`) foram pensadas para condicoes padronizadas. Para suas fotos
  reais, ajuste-as inspecionando os resultados com os utilitarios de debug
  (`board/debug.py`, `detection`).
- **Estimativa automatica da malha**: assume uma unica protoboard top-down e
  pode se confundir quando o enquadramento inclui multiplas secoes. Nesses
  casos, prefira a **calibracao assistida**.
- **Captura padronizada** (top-down, board inteira, iluminacao consistente)
  melhora muito a confiabilidade.
- **Componentes de 3+ pinos** (potenciometro, push button) sao representados por
  2 terminais aproximados (cantos inferiores do corpo) - suficiente para
  detectar deslocamento, mas sem inferir cada pino individualmente.
- **Separacao por area** depende da resolucao da foto (ex.: capacitor x botao).
  Os limites em `ComponentDetectionConfig` podem precisar de ajuste por camera.
- **API/SPA cobrem apenas o registro automatico**: os modos `--grid`/`--typed`
  (que exigem upload de calibracao) ficam disponiveis somente via CLI.
