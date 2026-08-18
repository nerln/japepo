# Metodología

## El problema

Al 18 de agosto de 2026 van tres galas y **ninguna eliminación publicada**. Lo
observado es esto y nada más:

- **Gala 1**, prueba individual de cortes: RDN nombra primero, segundo y tercero,
  y completa los seis destacados sin declarar el orden de los otros tres.
- **Gala 2**, prueba por equipos: tres tríos subieron al balcón y tres cayeron a
  la zona de riesgo, sin orden declarado dentro de cada grupo.
- **Gala 3**: se emitió el lunes 17 y ningún medio la contó. Un silencio no es un
  dato, así que no entra.

Un modelo honesto tiene que devolver algo parecido a dieciocho veces 5,6 %, y su
valor está en decir *cuánto* se apartó de ahí y por qué.

## El modelo

Cuatro piezas.

**Habilidad.** Cada persona tiene un número que no se ve, `theta_i`, sacado de
una normal de media cero y desviación `sigma`. En el caso base `sigma = 0,9`.

**La prueba individual.** El resultado de la gala 1 es un ranking ruidoso de esa
habilidad, modelado como Plackett-Luce sobre `exp(alpha_prueba * theta)`, con
`alpha_prueba = 0,6` en el caso base.

Los tres primeros puestos entran como secuencia ordenada. Los otros tres
destacados entran como **conjunto**: se suman las seis permutaciones posibles,
que es exactamente lo que significa «la lista se completó con estos tres» sin
decir en qué orden. Se ve en la página: esos tres salen iguales entre sí.

**La prueba por equipos.** El resultado de la gala 2 es un ranking ruidoso sobre
los seis **tríos**, no sobre las personas. La fuerza de un trío es el promedio de
las tres habilidades: el plato sale de los tres. Tres subieron y tres cayeron, sin
orden dentro de cada grupo, así que la verosimilitud suma las 3! × 3! = 36
ordenaciones compatibles.

`alpha_equipo` vale 0,35, más bajo que `alpha_prueba`, y la razón es simple: un
resultado repartido entre tres dice menos de cada uno que una prueba individual.

**Las galas.** En cada ronda se elimina a alguien con probabilidad proporcional a
`exp(-alpha_gala * theta)`. Se repite hasta que queda una persona.

### Cuánto movió cada observación

| Escenario | Ignorancia | Arriba |
| --- | --- | --- |
| Caso base, con las dos pruebas | 0,9635 | María Elsa Núñez, 10,9 % |
| Sin la prueba por equipos | 0,9680 | Joaquín Serrano, 10,8 % |
| Sin la prueba de cortes | 0,9982 | Marilina Bogado, 6,7 % |
| Sin ninguna de las dos | 0,9997 | el reparto plano, 5,6 % |

La gala 2 no es un detalle: **cambia quién puntea**. Con la prueba de cortes sola
el primero era Joaquín Serrano; su equipo cayó a la zona de riesgo y el de María
Elsa Núñez subió al balcón, y el orden se dio vuelta. Las dos observaciones juntas
bajan la ignorancia de 1 a 0,964, que sigue siendo casi todo lo que hay
para saber.

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

Esto **no** valida el modelo contra la realidad. La validación de verdad empieza
cuando haya eliminados, vive en `data/historial_pronostico.json` y se puntúa con
la regla que [EVALUACION.md](EVALUACION.md) fijó por adelantado: Brier
multiclase contra la baseline uniforme. `model/puntaje.py` se niega a puntuar
una gala que no tenía predicción publicada de antes.

## El calendario

Deducción con los supuestos escritos al lado. Quedan diecisiete eliminaciones y
hay dos emisiones por semana. Si cae una persona por emisión, la final llega en
unas ocho semanas y media; si cae una por semana, en diecisiete. La edición 2025
cerró el 17 de septiembre, que queda entre las dos cotas.

## Reproducir

La semilla es `20260810`, la fecha del estreno. Misma semilla, misma corrida.
La firma que aparece en el pie de la página es un hash de todo `data/`.
