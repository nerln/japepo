# japepo · notas para agentes

Página sobre MasterChef Celebrity Paraguay 2026, en castellano y guaraní. Se
publica desde `web/` en `main` por GitHub Actions.

## Antes de tocar nada

`python3 gui/verificar.py` tiene que dar cero. Es lo mismo que corre en CI y son
dieciocho comprobaciones. Después de cualquier cambio, tiene que seguir dando
cero.

## Las reglas que no se negocian

1. **Ningún número del modelo se escribe a mano.** Va como `{marcador}` en
   `data/i18n.json` y lo rellena `contexto()` en `gui/build.py`. La
   verificación rechaza un decimal en la prosa.
2. **Todo dato lleva `fuente`**, con un id que existe en `data/fuentes.json`.
3. **Los dos idiomas van siempre juntos.** Una clave nueva en `data/i18n.json`
   necesita `es` y `gn`, con los mismos marcadores en los dos. Los textos de
   `data/` llevan pares `*_es` / `*_gn`.
4. **Nada de fotos ni de logotipos ajenos.** Ver `LICENCIA.md`.
5. **La página no pide nada a otro servidor.** Sin fuentes remotas, sin CDN,
   sin embeds. Un `<img>` hace fallar la verificación.
6. **Un rumor entra con dos fuentes independientes.** Si hay una sola, no entra.
7. **La página es para quien mira el programa, no para quien la hizo.** Nada de
   explicar la metodología, la política de fotos o cómo está construido el
   sitio en la prosa de arriba: eso va en los `.md` del repo. Si una frase
   habla de «esta página», sobra.
8. **Ninguna tipografía del sistema.** Las tres familias se recortan y se
   incrustan con `gui/fuentes.py`; un titular en Georgia y un texto en la sans
   del sistema es lo que hace que una página se lea como una plantilla. Si un
   nombre nuevo trae una letra que el recorte no cubre, la verificación falla:
   se agrega a `CHARSET` y se vuelve a correr `gui/fuentes.py`.

9. **Lo que no se puede medir se dice, no se estima.** `model/social.py` publica
   el tamaño del corpus y la lista de corpus descartados con su motivo. Un
   porcentaje de sentimiento sacado de dieciséis comentarios sería inventado.
   Las vistas miden atención, y la palabra «atención» va en la página.
10. **Una promesa escrita no se reescribe.** `data/historial_pronostico.json` es
   append-only en sus tres series. Puntuar una gala cuya predicción no estaba
   publicada de antes no es puntuar: `model/puntaje.py` se niega y hace bien.
   La regla de puntuación está en `EVALUACION.md` y no se toca.

## La trampa que ya costó una vez en el proyecto vecino

En `placa`, los bloques de la plantilla se separaban con comentarios
`/* ---------- nombre ---------- */` y varios nombres existían dos veces, uno en
el CSS y otro en el JS: insertar buscando el marcador acertaba el equivocado y
el navegador se tragaba el JavaScript como CSS inválido sin decir nada.

Acá los puntos de inserción son comentarios HTML `<!--== NOMBRE ==-->`, que no
pueden aparecer dentro del CSS ni del guion. Los `/* ---------- */` que hay en
el `<style>` son solo para leer, y nadie inserta contra ellos. Si hace falta un
punto de inserción nuevo, va con la forma `<!--== ==-->` y `build.py` falla si
queda alguno sin llenar.

## El orden de las cosas

```
bin/publicar.sh       →  el camino entero, y el único que hace falta saber
gui/fuentes.py        →  gui/fuentes.css   (solo cuando cambia CHARSET)
model/preparacion.py  →  data/estadisticas.json
model/registrar.py    →  data/historial_pronostico.json (corridas, promesas)
model/puntaje.py      →  data/historial_pronostico.json (puntajes)
model/social.py       →  data/social.json   (solo con --social: tarda)
gui/build.py          →  web/index.html, web/datos.json
gui/verificar.py      →  el permiso para publicar
```

La firma de la corrida es un hash de todo `data/`, así que cualquier cosa que
escriba en `data/` va **antes** de `build.py`.

## Lo pendiente

Cuando empiecen las eliminaciones hay que sumarlas a la verosimilitud en
`model/preparacion.py`. Hasta entonces la ignorancia baja solo porque queda
menos gente. Está anotado en `ACTUALIZACION.md`.

## El guaraní

Lo escribió un modelo y no lo revisó ningún hablante, y la página lo dice. Una
corrección de un hablante gana sobre lo que haya escrito un agente: se aplica
sin discutir.
