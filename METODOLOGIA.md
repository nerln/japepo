# Metodología

## El problema

El 11 de agosto de 2026, cuando se armó esta página, MasterChef Celebrity
Paraguay llevaba una gala. No hubo ninguna eliminación. Lo único observado es
un orden parcial en una prueba técnica de cortes de vegetales: RDN nombra
primero, segundo y tercero, y después completa los seis destacados sin declarar
el orden de los otros tres.

Ese es todo el dato que existe. Un modelo honesto tiene que devolver algo muy
parecido a dieciocho veces 5,6 %, y su valor está en decir *cuánto* se apartó
de ahí y por qué.

## El modelo

Tres piezas.

**Habilidad.** Cada persona tiene un número que no se ve, `theta_i`, sacado de
una normal de media cero y desviación `sigma`. En el caso base `sigma = 0,9`.

**La prueba de cortes.** El resultado de la gala 1 es un ranking ruidoso de esa
habilidad, modelado como Plackett-Luce sobre `exp(alpha_prueba * theta)`. El
parámetro `alpha_prueba` es cuánto vale una prueba de cuchillo como predicción
de una temporada entera; en el caso base vale 0,6.

Los tres primeros puestos entran como secuencia ordenada. Los otros tres
destacados entran como **conjunto**: se suman las seis permutaciones posibles,
que es exactamente lo que significa «la lista se completó con estos tres» sin
decir en qué orden. El resultado se ve en la página: esos tres salen iguales
entre sí, porque la fuente no distingue entre ellos.

**Las galas.** En cada ronda se elimina a alguien con probabilidad proporcional
a `exp(-alpha_gala * theta)`. Quien cocina peor cae más seguido y nadie está a
salvo. Se repite hasta que queda una persona.

## Cómo se resuelve

Muestreo por importancia. Se sacan 200 000 partículas de la prior, se pesan con
la verosimilitud de la gala 1 y se remuestrean 1600. El tamaño efectivo de
muestra queda alrededor de 49 000, que es cómodo para 1600 draws.

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
| `sin_gala1` | `alpha_prueba = 0`. Devuelve el reparto plano exacto: es la vara para medir cuánto movió el único dato que hay. |
| `corte_manda` | `alpha_prueba = 1,6`. La prueba técnica predice fuerte. |
| `orden_completo` | Los tres destacados sin puesto se leen como ranking. Mide cuánto cambia leer la fuente de la forma más cargada. |
| `loteria` | `sigma = 0`. Todo es azar. |
| `plantel_parejo` | `sigma = 0,45`. |
| `plantel_disparejo` | `sigma = 1,6`. |

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
una habilidad verdadera de la prior, se simula una gala 1 con su orden parcial,
se corre la inferencia y se simula la temporada completa. Después se mira si el
ganador verdadero cae dentro del conjunto de mayor probabilidad al nivel
anunciado.

Los conjuntos salen algo conservadores: el nivel del 50 % acierta cerca del
55 %, y el del 90 % cerca del 94 %. Un intervalo conservador anuncia menos
certeza de la que tiene, que es el lado por el que conviene errar acá.

Esto **no** valida el modelo contra la realidad. La validación de verdad empieza
cuando haya eliminados, y vive en `data/historial_pronostico.json`: cada corrida
deja fecha, quién puntea, con cuánto y cuánta ignorancia quedaba. Dentro de dos
meses eso se lee contra lo que pasó.

## El calendario

Deducción con los supuestos escritos al lado. Quedan diecisiete eliminaciones y
hay dos emisiones por semana. Si cae una persona por emisión, la final llega en
unas ocho semanas y media; si cae una por semana, en diecisiete. La edición 2025
cerró el 17 de septiembre, que queda entre las dos cotas.

## Reproducir

La semilla es `20260810`, la fecha del estreno. Misma semilla, misma corrida.
La firma que aparece en el pie de la página es un hash de todo `data/`.
