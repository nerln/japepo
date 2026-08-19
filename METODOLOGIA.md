# Metodología

## El problema

Al 19 de agosto de 2026 van cuatro galas y **una eliminación**. Lo observado es
esto:

- **Gala 1**, prueba individual de cortes: primero, segundo y tercero declarados,
  y los otros tres destacados sin orden.
- **Gala 2**, prueba por equipos: tres tríos al balcón y tres a la zona de
  riesgo, sin orden dentro de cada grupo.
- **Gala 3**, zona de riesgo: de los nueve sentenciados, cuatro se salvaron y
  cinco quedaron abajo. Es un orden parcial entre esos nueve y nadie más.
- **Gala 4**: cayó Jessica Santa Cruz, de entre cinco.

## El modelo

Cinco piezas.

**Habilidad.** Cada persona tiene un número que no se ve, `theta_i`, sacado de
una normal de media cero y desviación `sigma`. En el caso base `sigma = 0,9`.

**La prueba individual.** Plackett-Luce sobre `exp(alpha_prueba * theta)`, con
`alpha_prueba = 0,6`. Los tres primeros entran como secuencia; los otros tres
destacados como conjunto, sumando las seis permutaciones.

**La prueba por equipos.** Plackett-Luce sobre los seis **tríos**, con la fuerza
de un trío igual al promedio de las tres habilidades. `alpha_equipo = 0,35`, más
bajo porque un resultado repartido entre tres dice menos de cada uno.

**La zona de riesgo.** Un orden parcial entre los sentenciados **y nadie más**:
el denominador son los nueve que compitieron esa noche. Meter a los otros nueve
sería decir que compitieron y perdieron.

**Las eliminaciones.** Cae quien cocina peor: probabilidad proporcional a
`exp(-alpha_gala * theta)` entre los que estaban en riesgo. Es la misma regla con
la que después se simula el resto de la temporada, y hasta el 18 de agosto no
había ninguna que cargar.

### Cuánto movió cada observación

| Escenario | Ignorancia | Arriba |
| --- | --- | --- |
| Caso base | 0,9510 | Joaquín Serrano, 12,7 % |
| Sin la prueba por equipos | 0,9523 | Joaquín Serrano, 14,2 % |
| Sin la prueba de cortes | 0,9977 | Maricha Olitte, 5,1 % |
| Sin ninguna de las dos pruebas | 0,9994 | queda sólo la eliminación |
| Lotería pura | 1,0000 | nadie: 5,9 % cada uno |

## El índice de ignorancia, y una corrección

Entropía de la distribución de ganadores dividida por la entropía máxima:

```
I = -sum(p log p) / log(m)
```

donde **m es la cantidad de gente que sigue en competencia**, no las dieciocho
del principio. La primera versión de este archivo dividía siempre por log(18), y
eso estaba mal: el índice habría bajado solo porque queda menos gente, midiendo
el paso del tiempo en vez de lo que se sabe. Con la normalización correcta, el
escenario de lotería pura da exactamente 1,000.

## Cómo se resuelve

Muestreo por importancia. Se sacan 200 000 partículas de la prior, se pesan con
la verosimilitud de las dos pruebas y se remuestrean 1600. El tamaño efectivo
de muestra queda alrededor de 46 000, que es cómodo para 1600 draws.

Cada draw corre 300 temporadas simuladas. El total se parte en ocho lotes, y la
dispersión entre lotes es de donde sale el error estándar que la página dibuja
como banda alrededor de cada barra. Ese número no es decoración: sin él, el
orden entre los primeros puestos se lee como si significara algo, y hoy no
significa nada. En la corrida publicada los dos primeros no se distinguen.

## El índice de ignorancia

Entropía de la distribución de ganadores dividida por la entropía máxima:

```
I = -sum(p log p) / log(n)
```

Vale uno cuando las dieciocho personas son indistinguibles y baja a cero cuando
queda una sola candidata. Es el número que la página pone arriba de todo, porque
es el que se mueve cuando pasa algo.

## Los escenarios

Cada escenario cambia un supuesto y vuelve a correr todo:

| Escenario | Qué cambia |
| --- | --- |
| `sin_nada` | Las dos observaciones en cero. Devuelve el reparto plano exacto: es la vara. |
| `sin_gala1` | `alpha_prueba = 0`. Queda sólo el resultado por equipos. |
| `sin_equipos` | `alpha_equipo = 0`. Es lo que la página decía antes de cargar la gala 2. |
| `corte_manda` | `alpha_prueba = 1,6`. La prueba técnica predice fuerte. |
| `orden_completo` | Los tres destacados sin puesto se leen como ranking. Mide cuánto cambia leer la fuente de la forma más cargada. |
| `loteria` | `sigma = 0`. Todo es azar. |
| `plantel_parejo` | `sigma = 0,45`. |
| `plantel_disparejo` | `sigma = 1,6`. |

## Lo que el modelo todavía no usa

**Las eliminaciones.** No porque falte código: porque al 18 de agosto no hay
ninguna publicada. Cuando aparezca la primera hay que sumarla a la verosimilitud;
está anotado en `ACTUALIZACION.md`.

**La gala 3.** Se emitió y ningún medio la contó. Un silencio no es un dato.

## Lo que el modelo no usa

**Las temporadas anteriores.** Hay cinco de MasterChef Paraguay y una sola de
Celebrity terminada. Con `n = 1` no se estima una tasa base por campo (música,
deporte, humor, televisión). La página muestra la historia como contexto y el
modelo le da peso cero. Cuando haya tres o cuatro ediciones de Celebrity, esto
se puede revisar.

**El voto del público.** Este formato lo decide el jurado, no una votación. No
hay encuestas que calibrar.

**El campo del que viene cada persona.** Catorce de las dieciocho tienen campo
declarado por la prensa y cuatro no. Aunque estuvieran las dieciocho, sin tasa
base no hay con qué convertir «cantante» en una probabilidad.

## La prueba de coherencia

No se puede validar el modelo contra la realidad todavía: no hay ni una
eliminación. Lo que sí se puede comprobar es que la maquinaria no se contradiga
a sí misma.

Se generan 200 temporadas sintéticas con el mismo proceso generativo: se saca
una habilidad verdadera de la prior, se simula una gala 1 con su orden parcial
**y una prueba por equipos con los mismos tríos**, se corre la inferencia y se
simula la temporada completa. Las observaciones sintéticas son las mismas que el
modelo usa de verdad: probarlo con menos sería hablar de otro modelo. Después se mira si el
ganador verdadero cae dentro del conjunto de mayor probabilidad al nivel
anunciado.

Los conjuntos salen algo conservadores: el nivel del 50 % acierta el
56,5 %, el del 80 % el 82,5 % y el del 90 % el 92,0 %. Un intervalo conservador anuncia menos
certeza de la que tiene, que es el lado por el que conviene errar acá.

Esto **no** valida el modelo contra la realidad. Eso lo hace el puntaje, con la
regla que [EVALUACION.md](EVALUACION.md) fijó por adelantado.

## El primer puntaje

La predicción para la gala 4 se publicó el **18 de agosto a las 07:31 UTC**, en
el commit `de296f3`, unas dieciséis horas antes de que la gala saliera al aire.
Ponía a Jessica Santa Cruz **2ª de 18** entre las que podían caer, con
6,9 %. Cayó ella.

| | Modelo | Uniforme |
| --- | --- | --- |
| Brier | 0,9213 | 0,9444 |
| Log-loss | 2,681 | 2,890 |

El modelo le gana a la baseline. Con **una** gala puntuada eso no dice casi
nada: la diferencia es chica y una sola observación no distingue un modelo que
sirve de uno con suerte. Lo que sí queda establecido es el procedimiento, y que
la predicción es verificable por cualquiera sin creerle a nadie:

```bash
git show de296f3:data/historial_pronostico.json | python3 -c "import json,sys; print(json.load(sys.stdin)['predicciones_gala'][-1]['p_cae'])"
```

## El calendario

Deducción con los supuestos escritos al lado. Quedan diecisiete eliminaciones y
hay dos emisiones por semana. Si cae una persona por emisión, la final llega en
unas ocho semanas y media; si cae una por semana, en diecisiete. La edición 2025
cerró el 17 de septiembre, que queda entre las dos cotas.

## Reproducir

La semilla es `20260810`, la fecha del estreno. Misma semilla, misma corrida.
La firma que aparece en el pie de la página es un hash de todo `data/`.
