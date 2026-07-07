# Pipeline de visao — as 6 etapas

Este documento descreve o que o sistema faz com as duas fotos, na mesma ordem
do diagrama de blocos do projeto. Na interface web, cada etapa aparece durante o
carregamento e depois no painel **Auditoria do processamento**.

## 1. Imagem

Recebemos o par de fotos:

- **Gabarito** — circuito correto de referencia
- **Aluno** — circuito montado pelo estudante

Nesta etapa apenas organizamos as entradas. Nenhuma comparacao acontece ainda.

## 2. Alinhamento

As duas fotos raramente tem o mesmo enquadramento. Usamos **SIFT + homografia**
para sobrepor a foto do aluno sobre a do gabarito.

**Por que importa:** depois do alinhamento, o pixel `(x, y)` nas duas imagens
representa o mesmo ponto fisico da protoboard.

## 3. Subtracao

Com as fotos alinhadas, calculamos onde a **ocupacao** mudou:

- **Vermelho** — estava no gabarito e sumiu no aluno
- **Verde** — apareceu no aluno e nao estava no gabarito

Essas regioes sao candidatas a divergencia (componente movido, faltando ou
sobrando).

## 4. Filtro da media

Antes de decidir o que e componente e o que e fundo, aplicamos um **filtro
gaussiano** no canal de **saturacao** (HSV).

**Por que importa:** reduz ruido da camera e realca fios e corpos coloridos
(LED, resistor, jumpers) sobre o plastico bege da protoboard.

## 5. Binarizacao

Convertemos a saturacao filtrada em **mascaras binarias**:

- **Branco** — regiao ocupada por componente colorido
- **Preto** — fundo ou furo vazio

Comparamos as mascaras do gabarito e do aluno para isolar o que mudou.

## 6. Extracao de caracteristicas

Agrupamos os pixels alterados em **clusters** (regioes conectadas), rotulamos
pela cor dominante (ex.: "componente azul", "componente laranja") e pareamos
regioes proximas entre gabarito e aluno.

O par mais **saliente** vira a **divergencia principal** exibida na interface.

## Reducao de ruido

Fotos reais geram artefatos de alinhamento. O sistema aplica:

- dilatacao maior na subtracao (tolerancia a subpixel)
- fusao de blobs vizinhos da mesma cor
- descarte de `missing`/`extra` com saliencia muito baixa
- modo **um erro por placa** na interface (toggle para ver todas em debug)

## Limitacoes

- Componentes de **baixa saturacao** (fio preto, LDR cinza) sao dificeis de ver
  por este metodo.
- Funciona melhor com fotos **top-down**, mesma placa e iluminacao parecida.
- O rotulo e pela **cor**, nao pelo tipo exato (resistor vs LED) quando a regiao
  de diferenca e pequena.

Para modos alternativos (deteccao por tipo, malha calibrada), veja
[desenvolvimento.md](desenvolvimento.md).
