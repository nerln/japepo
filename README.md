# japepo

Pronóstico, plantel, galas y estadísticas de **MasterChef Celebrity Paraguay
2026**, en castellano y en guaraní, con seis temas de color.

La temporada empezó el lunes 10 de agosto de 2026 por el SNT. Cuando esta
página se armó había una gala jugada y ninguna eliminación, así que su trabajo
no es decir quién gana: es decir cuánto se puede saber con una sola gala, y
poner un número a ese poco.

*japepo* es «olla» en guaraní.

## Qué hay adentro

| Sección | Qué muestra |
| --- | --- |
| Arriba de todo | Cuándo es la próxima gala, cuánto falta y dónde verla |
| La próxima gala | El desafío, qué está en juego, los capitanes y el calendario |
| Quiénes cocinan | Las 18 personas, de dónde vienen y qué chance tienen |
| Cómo va | La chance de cada uno, con el margen de error dibujado |
| Las galas | Una por emisión, con los momentos de cada noche |
| Lo que ya se sabe | Spoilers, cerrados hasta que el lector los abra |
| Dónde seguirlo | Las cuentas oficiales, las etiquetas y los tuits |
| La ficha | Canal, horario, conducción, jurado, premio |
| Cómo se hizo | El modelo, sus límites, y el detalle para quien lo quiera |
| Qué mira la gente | Las vistas de los dieciocho videos de presentación, y por qué el jurado y el público no miran a la misma persona |
| El registro | Lo que se dijo antes de cada gala, cuánto se acercó, y todas las versiones publicadas |

El orden es el de quien mira el programa. El modelo y su letra chica van al
final, que es donde los busca quien los busca.

## Cómo correrlo

```bash
bin/publicar.sh                 # el camino entero: recalcula, comprueba y publica
bin/publicar.sh --gala 5        # además congela la predicción para la gala 5
bin/publicar.sh --social        # vuelve a medir vistas y comentarios
bin/publicar.sh --sin-empujar   # deja el commit hecho y no lo manda
```

Si falla cualquiera de las dieciocho comprobaciones, no publica y sale con
error. Es lo que permite que esto pueda correr sin que nadie lo mire.

Los pasos por separado, cuando hace falta:

```bash
python3 model/preparacion.py                     # el modelo → data/estadisticas.json
python3 model/registrar.py --fecha AAAA-MM-DD --gala N   # congela la corrida y la promesa
python3 model/puntaje.py --gala N                # puntúa una gala ya resuelta
python3 model/social.py --fecha AAAA-MM-DD       # vistas y comentarios → data/social.json
python3 gui/fuentes.py                           # recorta e incrusta las tipografías
python3 gui/build.py                             # arma web/index.html desde data/
python3 gui/tarjeta.py                           # la tarjeta de previsualización y el icono
python3 gui/verificar.py                         # el portero
```

Hace falta Python 3.12 con numpy, fonttools y Pillow, y node para una de las
comprobaciones. El modelo tarda alrededor de un minuto y se queda por debajo de
150 MB. `gui/fuentes.py` se corre solo cuando cambia el juego de signos: deja
hecho `gui/fuentes.css`, que va commiteado.

## La tipografía

Tres familias, tres trabajos, ninguna del sistema:

| Familia | Dónde | Por qué |
| --- | --- | --- |
| Be Vietnam Pro | Titulares, rótulos, nombres | Grotesco geométrico dibujado para el vietnamita, que lleva las mismas vocales con tilde que el guaraní: la ĩ, la ẽ, la õ, la ũ y la ỹ están dibujadas, no compuestas al vuelo |
| Source Serif 4 | Todo lo que se lee de corrido | Serif de pantalla; el eje óptico queda fijo en once puntos, que es el tamaño al que trabaja |
| Source Code | Las cifras | En esta página las cifras forman columna y tienen que alinearse |

Las tres bajo SIL Open Font License 1.1, recortadas al juego de signos que la
página usa y metidas adentro del HTML como data URI: no se pide un archivo a
nadie. Si algún día aparece un nombre con una letra que el recorte no trae,
`gui/verificar.py` lo dice antes de publicar en vez de dejar un renglón con dos
letras de otra tipografía.

## Cómo se actualiza después de cada gala

En [ACTUALIZACION.md](ACTUALIZACION.md). Resumen: se carga la gala en
`data/galas.json`, se marca al eliminado en `data/plantel.json`, y se vuelve a
correr la secuencia de arriba.

## Lo que se puede medir del público, y lo que no

Este programa casi no tiene conversación pública, y eso es una cuenta, no una
impresión. `model/social.py` deja escritos los seis corpus que se probaron y por
qué cinco no sirven: los comentarios de los episodios no devuelven nada, Facebook
pide sesión, Instagram y TikTok piden credenciales, X está quieto, y al widget de
comentarios de Popular no se llegó. Lo que sí se puede medir son las vistas de
los dieciocho videos de presentación, que son del mismo canal, del mismo día y
del mismo formato: uno por participante.

Miden **atención, no aprobación**, y la página lo dice antes de mostrar la
primera barra.

## El primer puntaje

La predicción para la gala 4 se publicó el 18 de agosto a las 07:31 UTC, en el
commit `de296f3`, dieciséis horas antes de la emisión. Ponía a Jessica Santa Cruz
segunda de dieciocho entre las que podían caer. Cayó ella, y el Brier del modelo
(0,921) le gana al de la uniforme (0,944).

Con una sola gala puntuada eso no dice casi nada, y la página lo dice así. Lo que
queda establecido es el procedimiento: la predicción está en un commit público
anterior a la gala y cualquiera puede leerla sin creerle a nadie.

## Cómo se sabe si el pronóstico sirve

[EVALUACION.md](EVALUACION.md) fija cómo se puntúa **antes** de que termine la
temporada: Brier multiclase sobre quién cae, contra la baseline uniforme, y
log-loss sobre quién gana. Declarar la predicción sin declarar la métrica no
sirve de nada: al final se elige la que conviene y se lee como excusa.

Cada corrida congela en `data/historial_pronostico.json` tres cosas que no se
reescriben nunca: la foto del día, la promesa para la gala siguiente, y el
puntaje cuando esa gala se resuelve. `model/puntaje.py` se niega a puntuar una
gala que no tenía predicción publicada de antes.

## Las reglas de la casa

- **Todo dato lleva fuente.** Cada afirmación de la página apunta a una entrada
  de `data/fuentes.json`, y `gui/verificar.py` rechaza una fuente que no exista.
- **Ningún número se escribe a mano.** Si sale del modelo, entra como marcador
  y lo rellena `gui/build.py`. La verificación rechaza un decimal escrito en la
  prosa.
- **Nada de fotos de los participantes.** Cada persona entra con una figura
  generada a partir de su nombre.
- **La página no pide nada a ningún otro servidor.** Funciona sin red y no
  registra a nadie por abrirla. Los tuits se leen acá y el original se abre
  solo si el lector aprieta el enlace.
- **Un rumor entra con dos fuentes independientes.** Sin eso no entra.

## El guaraní

Lo escribió una máquina y no lo revisó ningún hablante. Si algo está mal dicho,
la corrección es bienvenida: se abre un issue o se manda un parche sobre
`data/i18n.json` y los campos `*_gn` de `data/`.

## Aviso

Página de análisis independiente. No tiene relación con MasterChef, con
Banijay, con el SNT ni con la producción del programa. Las marcas nombradas son
de sus dueños y se nombran para decir de qué trata el análisis. La marca de esta
página es una olla vista desde arriba y no reproduce ningún logotipo ajeno.

## Licencia

Código con Apache-2.0 ([LICENSE](LICENSE)), textos y datos con CC BY 4.0. Ver
[LICENCIA.md](LICENCIA.md).

Hecho por [nerln](https://github.com/nerln) · [@nerellone](https://x.com/nerellone)
