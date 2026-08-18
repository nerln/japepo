# Cómo se actualiza después de cada gala

El programa va lunes y martes a las 20:50. La secuencia completa tarda un par
de minutos.

## 1. Cargar lo que pasó

**`data/galas.json`** — la gala que se emitió pasa de `"estado": "anunciada"` a
tener sus datos, y se agrega la siguiente si ya se anunció. Los campos que
importan:

```json
{
  "n": 3,
  "fecha": "2026-08-17",
  "titulo_es": "...", "titulo_gn": "...",
  "prueba": "eliminacion",
  "prueba_detalle_es": "...", "prueba_detalle_gn": "...",
  "eliminado": "id_de_la_persona",
  "destacados": { "ordenados": [], "sin_orden": [] },
  "fuente": "id_de_la_fuente"
}
```

Si la fuente nombra un podio sin declarar el orden, va en `sin_orden`. Esa
distinción no es cosmética: el modelo suma las permutaciones y devuelve a esas
personas empatadas entre sí. Meterlas en `ordenados` es afirmar algo que la
fuente no dijo.

**`data/plantel.json`** — a quien salió se le pone `"estado": "eliminado"`.

**`data/fuentes.json`** — si la nota es de un medio que todavía no está, se
agrega con medio, título, url, fecha y fecha de consulta. Una fuente que no
existe hace fallar la verificación.

## 2. Correr

```bash
python3 model/puntaje.py --gala N        # puntúa la gala que se acaba de resolver
bin/publicar.sh --gala N+1               # recalcula, congela la promesa siguiente y publica
```

`bin/publicar.sh` hace todo lo demás: corre el modelo, escribe la corrida en el
registro, sella la corrida anterior con el commit desde el que salió publicada,
rearma la página y la tarjeta, pasa las dieciocho comprobaciones y empuja. Si
alguna falla, no publica.

El puntaje va **primero**, y el orden no es capricho: `puntaje.py` lee la
promesa que quedó escrita antes de esa gala, y `publicar.sh` escribe la
siguiente. Si se invierten, se puntúa contra una predicción hecha después de
saber el resultado, que es exactamente lo que este registro existe para
impedir. `model/puntaje.py` igual se niega, pero conviene no tentarlo.

Los pasos por separado, si hace falta:

```bash
python3 model/preparacion.py
python3 model/registrar.py --fecha AAAA-MM-DD --gala N
python3 gui/build.py
python3 gui/tarjeta.py
python3 gui/verificar.py
```

**Antes de todo eso**, en `data/programa.json`, mover `proxima_gala` a la fecha
de la emisión siguiente. De ahí salen la tarjeta de arriba de la página, el
calendario y la imagen que se ve cuando alguien comparte el enlace. Si no se
mueve, la página sigue anunciando una gala que ya pasó hasta que el visitante
tenga JavaScript: el guion la corrige sola en el navegador, pero la versión
estática y la tarjeta de previsualización se quedan viejas.

`gui/fuentes.py` no hace falta en la actualización de cada gala: las
tipografías ya están recortadas y commiteadas. Solo se vuelve a correr si la
verificación avisa que la página usa un signo que el recorte no trae, y en ese
caso hay que agregar el signo a `CHARSET` primero.

El orden importa: `registrar.py` escribe en `data/`, y la firma de la corrida es
un hash de `data/`, así que `build.py` va después.

## 3. Publicar

```bash
git add -A && git commit && git push
```

`gui/verificar.py` es lo mismo que corre en CI. Si pasa acá, pasa allá.

## Lo que hay que revisar a mano de vez en cuando

- **`METODOLOGIA.md` tiene números escritos a mano.** El tamaño efectivo de
  muestra, los porcentajes de la calibración y las semanas del calendario
  cambian con cada corrida. La verificación no los mira, porque no están en la
  página. Conviene repasarlos cuando cambie algo del modelo.
- **El premio de 2026.** Está cargado el de 2025 con su aviso. Cuando la
  producción publique el de esta edición, va en `data/programa.json` y se saca
  `"premio_2026_confirmado": false`.
- **Los cuatro campos sin confirmar.** Joaquín Serrano, Vale Vierci, Jessica
  Santa Cruz y Marisa Monutti entraron sin descripción de la prensa. Si aparece
  una fuente, se completa `campo` y `campo_fuente`.
- **El modelo ignora las temporadas anteriores.** Cuando haya tres o cuatro
  ediciones de Celebrity terminadas se puede estimar una tasa base por campo.
  Hoy hay una.

## Cuando empiecen las eliminaciones

El modelo actual usa una sola observación: el orden parcial de la gala 1. En
cuanto haya eliminados, cada eliminación es información nueva y hay que sumarla
a la verosimilitud en `model/preparacion.py`, en la función
`log_verosimilitud`. Mientras eso no se haga, el índice de ignorancia va a
bajar solo porque quedan menos personas, no porque el modelo aprenda. Es el
primer trabajo pendiente del proyecto.
