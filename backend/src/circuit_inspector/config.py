"""Configuracao central do Circuit Inspector.

Concentra parametros ajustaveis (geometria do board, faixas HSV de cores,
tolerancias) em um unico lugar para permitir tuning sem alterar a logica.

Toda a deteccao classica (segmentacao por cor, deteccao de malha, mapeamento
geometrico) le seus parametros daqui. Os defaults foram pensados para fotos
top-down padronizadas, mas sao facilmente sobrescritiveis em testes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Geometria da protoboard
# ---------------------------------------------------------------------------

# Linhas da area central, de cima para baixo na orientacao canonica.
# A protoboard padrao tem um canal central entre as linhas "e" e "f".
TOP_ROWS: tuple[str, ...] = ("j", "i", "h", "g", "f")
BOTTOM_ROWS: tuple[str, ...] = ("e", "d", "c", "b", "a")

# Nomes das trilhas de alimentacao (power rails).
RAIL_POSITIVE = "+"
RAIL_NEGATIVE = "-"


@dataclass(frozen=True)
class BoardLayout:
    """Descreve a geometria logica da protoboard.

    `min_column`/`max_column` definem a faixa de colunas presente nas fotos
    padronizadas. Como ambas as imagens sao retificadas para o mesmo frame
    canonico, esses indices identificam o mesmo furo fisico nas duas fotos.
    """

    min_column: int = 1
    max_column: int = 63
    top_rows: tuple[str, ...] = TOP_ROWS
    bottom_rows: tuple[str, ...] = BOTTOM_ROWS
    rail_positive: str = RAIL_POSITIVE
    rail_negative: str = RAIL_NEGATIVE

    @property
    def rows(self) -> tuple[str, ...]:
        """Todas as linhas da area central, de cima para baixo."""
        return self.top_rows + self.bottom_rows

    @property
    def column_count(self) -> int:
        return self.max_column - self.min_column + 1


# ---------------------------------------------------------------------------
# Faixas de cor (HSV) para segmentacao
# ---------------------------------------------------------------------------

# OpenCV usa H em [0, 179], S e V em [0, 255].
HsvBound = tuple[int, int, int]


@dataclass(frozen=True)
class HsvRange:
    """Uma faixa HSV (inclusiva). Vermelho usa duas faixas por causa do wrap
    do matiz em 0/180, por isso `extra_lower`/`extra_upper` sao opcionais."""

    lower: HsvBound
    upper: HsvBound
    extra_lower: HsvBound | None = None
    extra_upper: HsvBound | None = None

    @property
    def is_split(self) -> bool:
        return self.extra_lower is not None and self.extra_upper is not None


@dataclass(frozen=True)
class ColorProfiles:
    """Faixas HSV nomeadas usadas pelos detectores baseados em cor.

    - `red`/`orange`/`green`/`black`: cores de jumpers.
    - `led_blue`/`led_red`: corpo translucido do LED (por cor).
    - `resistor_body`: corpo do resistor de filme metalico (azul/verde-azulado).
    - `ldr_body`/`metallic`: corpos metalicos acinzentados (LDR / potenciometro).
    - `dark_body`: corpos escuros (capacitor eletrolitico / push button).
    """

    red: HsvRange = HsvRange(
        lower=(0, 90, 60),
        upper=(10, 255, 255),
        extra_lower=(170, 90, 60),
        extra_upper=(179, 255, 255),
    )
    orange: HsvRange = HsvRange(lower=(11, 120, 90), upper=(22, 255, 255))
    green: HsvRange = HsvRange(lower=(36, 60, 50), upper=(85, 255, 255))
    black: HsvRange = HsvRange(lower=(0, 0, 0), upper=(179, 90, 70))
    led_blue: HsvRange = HsvRange(lower=(105, 120, 80), upper=(130, 255, 255))
    led_red: HsvRange = HsvRange(
        lower=(0, 110, 90),
        upper=(10, 255, 255),
        extra_lower=(170, 110, 90),
        extra_upper=(179, 255, 255),
    )
    resistor_body: HsvRange = HsvRange(lower=(85, 60, 60), upper=(104, 255, 255))
    ldr_body: HsvRange = HsvRange(lower=(0, 0, 90), upper=(179, 55, 190))
    metallic: HsvRange = HsvRange(lower=(0, 0, 90), upper=(179, 55, 200))
    dark_body: HsvRange = HsvRange(lower=(0, 0, 0), upper=(179, 90, 70))

    def wire_colors(self) -> dict[str, "HsvRange"]:
        """Faixas de cor consideradas como possiveis jumpers."""
        return {
            "red": self.red,
            "orange": self.orange,
            "green": self.green,
            "black": self.black,
        }

    def led_colors(self) -> dict[str, "HsvRange"]:
        """Faixas de cor consideradas como possiveis LEDs."""
        return {"blue": self.led_blue, "red": self.led_red}


# ---------------------------------------------------------------------------
# Parametros de deteccao da malha de furos
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HoleDetectionConfig:
    """Parametros do blob detector usado para localizar os furos."""

    min_area: float = 6.0
    max_area: float = 400.0
    min_circularity: float = 0.55
    min_inertia_ratio: float = 0.3
    # Distancia maxima (em fracao do passo da malha) para considerar dois furos
    # como pertencentes a mesma linha/coluna ao agrupar.
    grid_cluster_tolerance: float = 0.4


# ---------------------------------------------------------------------------
# Tolerancias gerais
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentDetectionConfig:
    """Parametros de forma/area usados pelos detectores de componente.

    Areas sao em pixels^2. `*_aspect` e a razao lado_maior/lado_menor do
    retangulo minimo; usado para separar componentes alongados (fios,
    resistores) de compactos (LED, LDR, capacitor, potenciometro, botao).
    Os limites de area/circularidade tambem separam componentes que
    compartilham cor (ex.: capacitor x botao, ambos escuros).
    """

    # Alongados
    min_wire_area: float = 150.0
    min_wire_aspect: float = 2.2
    min_resistor_area: float = 200.0
    min_resistor_aspect: float = 1.8

    # LED (compacto, circular)
    led_min_area: float = 120.0
    led_max_area: float = 8000.0
    led_min_circularity: float = 0.6

    # LDR (compacto, cinza, pequeno)
    ldr_min_area: float = 150.0
    ldr_max_area: float = 8000.0
    ldr_min_circularity: float = 0.6

    # Capacitor eletrolitico (escuro, redondo, grande).
    # Separado do botao primariamente pela area maior.
    capacitor_min_area: float = 1500.0
    capacitor_max_area: float = 200000.0
    capacitor_min_circularity: float = 0.7

    # Potenciometro (metalico cinza, grande)
    potentiometer_min_area: float = 8000.0
    potentiometer_max_area: float = 500000.0
    potentiometer_min_circularity: float = 0.55

    # Push button (escuro, quadrado, pequeno/medio - menor que o capacitor)
    button_min_area: float = 400.0
    button_max_area: float = 1500.0
    button_min_circularity: float = 0.45
    button_max_circularity: float = 0.85
    button_max_aspect: float = 1.4


@dataclass(frozen=True)
class OccupancyConfig:
    """Parametros da deteccao estrutural por ocupacao de furo.

    A ocupacao e medida pela *saturacao* (HSV) ao redor de cada furo: componentes
    coloridos (resistor, LED, jumpers) elevam a saturacao acima do fundo bege da
    protoboard, enquanto furos vazios e o corpo cinza do LDR ficam proximos do
    fundo. Os limiares sao *adaptativos*: calculados a partir da saturacao
    mediana do board (robustez a iluminacao/camera).

    - `patch_radius_frac`: raio do patch de amostragem, como fracao do passo
      local da malha (escala-invariante).
    - `occupied_delta`/`empty_delta`: quanto a saturacao precisa exceder o fundo
      para o furo contar como ocupado / continuar vazio (histerese).
    - `min_cluster_strength`: soma minima de |ΔS| de um agrupamento para ser
      considerado uma diferenca real (descarta ruido de borda).
    - `alignment_dilate_kernel`: dilatacao na subtracao para tolerar subpixel
      de alinhamento SIFT.
    - `pair_max_distance_frac`: fracao da diagonal usada como raio maximo para
      parear clusters (gabarito x aluno).
    - `min_salience_ratio`: descarta missing/extra abaixo desta fracao da
      saliencia do cluster mais forte.
    - `merge_cluster_distance_px`: funde blobs vizinhos da mesma cor antes de
      parear (0 = desligado).
    - `include_dark_bodies`: inclui botao/capacitor via mascara de corpo escuro.
    - `dark_s_max`: saturacao maxima para contar pixel como corpo escuro.
    - `mismatch_min_displacement_px`: abaixo disso, salience de mismatched e
      penalizada (artefato de alinhamento).
    - `diff_cluster_min_area`/`diff_cluster_area_frac`: limiar menor para blobs
      em mascaras de diferenca (fios finos).
    """

    patch_radius_frac: float = 0.33
    occupied_delta: float = 40.0
    empty_delta: float = 15.0
    min_cluster_strength: float = 60.0
    alignment_dilate_kernel: int = 9
    pair_max_distance_frac: float = 0.12
    min_salience_ratio: float = 0.20
    merge_cluster_distance_px: int = 40
    include_dark_bodies: bool = True
    dark_s_max: int = 80
    diff_cluster_min_area: int = 200
    diff_cluster_area_frac: float = 0.00005
    mismatch_min_displacement_px: float = 40.0


@dataclass(frozen=True)
class MatchingConfig:
    """Tolerancias usadas no mapeamento e na comparacao."""

    # Raio maximo (em pixels no frame canonico) para associar um terminal
    # detectado ao furo mais proximo.
    terminal_snap_radius: float = 30.0
    # Distancia minima entre os dois terminais de um componente (em furos),
    # usada para descartar deteccoes degeneradas.
    min_terminal_separation: float = 1.0


@dataclass(frozen=True)
class InspectorConfig:
    """Agrega toda a configuracao do pipeline."""

    board: BoardLayout = field(default_factory=BoardLayout)
    colors: ColorProfiles = field(default_factory=ColorProfiles)
    holes: HoleDetectionConfig = field(default_factory=HoleDetectionConfig)
    components: ComponentDetectionConfig = field(
        default_factory=ComponentDetectionConfig
    )
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    occupancy: OccupancyConfig = field(default_factory=OccupancyConfig)


DEFAULT_CONFIG = InspectorConfig()
"""Instancia de configuracao padrao usada quando nenhuma e fornecida."""
