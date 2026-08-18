# Cómo se va a puntuar este pronóstico

Este archivo se escribe **antes** de que termine la temporada y no se toca
después. Declarar la predicción sin declarar cómo se la mide no sirve de nada:
al final se elige la métrica que conviene y se lee como excusa.

Lo que se fija acá: qué se mide, contra qué se compara, con qué datos, y qué
pasa si el SNT mueve una fecha.

Escrito el **18 de agosto de 2026 a las 07:31 UTC**, con la corrida
`4d96c96d322d`, sobre el commit `1b2355a`.

Ese hash es el de los datos publicados el día en que se congeló esta regla y
sirve para recuperar ese estado exacto del repositorio. Se mueve cada vez que se
publica cualquier dato nuevo. Lo que no se mueve es lo escrito acá abajo.

**Y una cosa más, que es la que le da sentido a la fecha de arriba:** cuando se
escribió este archivo yo todavía no sabía qué había pasado en las galas del 11
al 18 de agosto. La búsqueda que reconstruye esa semana se lanzó antes y todavía
no había vuelto. Se escribió primero la regla y después se miraron los
resultados, en ese orden, a propósito.

---

## Las dos preguntas, que se puntúan por separado

La página contesta dos cosas distintas y son de dificultad muy distinta.

### Pregunta 1: quién cae en cada gala

Antes de cada gala de eliminación, el modelo publica una probabilidad de caída
para cada persona en competencia. Queda congelada en la serie
`predicciones_gala` de `data/historial_pronostico.json`, que es append-only, y
se puntúa con **Brier multiclase** sobre las personas que estaban en
competencia esa noche:

    BS = Σ_i (p_i − y_i)²        y_i = 1 para quien salió, 0 para los demás

Más bajo es mejor. Se reporta gala por gala y el promedio.

**Baseline, fijada ahora:** la **uniforme** sobre quienes quedan, p_i = 1/n. Es
la que hay que ganar para poder decir que el modelo aporta algo. Con dieciocho
personas la uniforme da un Brier de 0,9444; con diez, de 0,9000.

No hay segunda baseline. No se encontró ningún mercado de apuestas con volumen
real sobre este programa, y si aparece uno se lo declara acá antes de usarlo, no
después. Si no aparece, se dice que no hubo segunda baseline en vez de
sustituirla por cualquier otra cosa.

Se reporta además el **puesto** en que la predicción dejó al que efectivamente
salió, sobre cuántos había. Es lo que se entiende sin saber qué es un Brier: si
lo tenía tercero de dieciocho, algo vio; si lo tenía decimoquinto, no vio nada.

### Pregunta 2: quién gana la edición

Se puntúa con **log-loss** sobre la distribución del ganador publicada en cada
corrida:

    LL = −log p(ganador real)

Se calcula al final, para cada fecha de corrida guardada en la serie `corridas`
de `data/historial_pronostico.json`. La serie completa muestra si el modelo se
fue acercando o se quedó dando vueltas. La baseline es la uniforme sobre los que
quedaban esa fecha.

## Qué se puede puntuar y qué no

Sólo se puntúa una gala si **la promesa estaba escrita antes**. `model/puntaje.py`
se niega a puntuar una gala sin entrada previa en `predicciones_gala`, y hace
bien: puntuar una predicción escrita después de conocer el resultado no es
puntuar, es redactar.

La primera promesa de esta temporada es la que se publicó el **11 de agosto de
2026**, en el commit `3936c99`, antes de la gala del martes 11. Está en el
`web/datos.json` de ese commit y se puede leer sin creerme:

```bash
git show 3936c99:web/datos.json | python3 -c "import json,sys; print(json.load(sys.stdin)['estadisticas']['escenarios']['base']['p_proxima'])"
```

Si esa gala tuvo eliminación, se puntúa con esa distribución y con ninguna otra.

## Lo que ya se sabe y queda registrado acá

Cuando se congela esta regla, el modelo lleva **una sola observación**: el orden
parcial de la prueba de cortes de la gala 1. El índice de ignorancia da 0,966
sobre un máximo de 1, y el escenario `sin_gala1` devuelve el 1/18 exacto. Con
eso, la expectativa declarada es que las primeras galas salgan mal o apenas
mejor que la uniforme, y que el modelo empiece a servir para algo recién cuando
haya varias eliminaciones cargadas.

Hay además un agujero conocido y anotado en `ACTUALIZACION.md`: las
eliminaciones todavía no entran en la verosimilitud del modelo. Hasta que entren,
la ignorancia baja sólo porque queda menos gente. Si el modelo mejora después de
taparlo, la comparación honesta es contra las galas puntuadas antes del cambio,
no contra la uniforme.

## Si el canal mueve una fecha

Si el SNT cambia el día de una emisión, la promesa vale para la gala por su
**número**, no por su fecha. Si una emisión no tiene eliminación, no se puntúa y
la promesa escrita para ella se traslada a la siguiente sólo si la corrida no
cambió; si cambió, se escribe una nueva y se puntúa esa.

Si la temporada se corta o el programa cambia de formato, se cierra el puntaje
con las galas que haya y se dice cuántas fueron.
