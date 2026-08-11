# Licencias de terceros

## Tipografías

La página incrusta tres familias, las tres bajo **SIL Open Font License 1.1**,
que permite el uso, la modificación y la redistribución incluso incrustadas en
un documento, siempre que el aviso de licencia viaje con ellas. Acá viaja en
tres lugares: dentro del binario recortado (se conservan los campos de nombre 0,
13 y 14 al recortar), en la cabecera de `gui/fuentes.css` —que se copia entera
adentro del HTML publicado— y en los archivos completos de `gui/tipos/`.

- **Be Vietnam Pro** — The Be Vietnam Pro Project Authors.
  https://github.com/bettergui/BeVietnamPro
  Pone los títulos, los rótulos y los nombres. Está dibujada para el vietnamita,
  que lleva las mismas vocales con tilde que el guaraní.
  Licencia: [`gui/tipos/OFL-BeVietnamPro.txt`](gui/tipos/OFL-BeVietnamPro.txt)

- **Source Serif 4** — Adobe, con nombre reservado «Source».
  https://github.com/adobe-fonts/source-serif
  Pone todo lo que se lee de corrido. En la página viaja con el eje óptico
  fijado en once puntos y el de peso recortado a 250–700.
  Licencia: [`gui/tipos/OFL-SourceSerif4.txt`](gui/tipos/OFL-SourceSerif4.txt)

- **Source Code** — Adobe, con nombre reservado «Source».
  https://github.com/adobe-fonts/source-code-pro
  Pone las cifras, que en esta página forman columna.
  Licencia: [`gui/tipos/OFL-SourceCode.txt`](gui/tipos/OFL-SourceCode.txt)

Las tres viajan recortadas al juego de signos que la página usa; el recorte lo
hace `gui/fuentes.py` con fontTools.

**Por qué dos de las tres cambian de nombre.** Recortar una fuente es
modificarla. La propia licencia define «Modified Version» como cualquier
derivado hecho borrando componentes o cambiando el formato, y el FAQ oficial de
la OFL contesta que sí, que hacer un subconjunto para la web cuenta como
modificación. Las dos familias de Adobe llevan nombre reservado —«Source»— y la
cláusula 3 prohíbe usar ese nombre en una versión modificada. La excepción por
equivalencia funcional exige el mismo inventario de caracteres, y acá Source
Serif 4 pasa de 1464 glifos a 292. Por eso los recortes se publican como
**Japepo Serif** y **Japepo Mono**, y el crédito a Adobe queda escrito en el pie
de la página, acá, y adentro de cada binario. Be Vietnam Pro no lleva nombre
reservado, así que conserva el suyo.

En la cadena de respaldo del CSS los nombres originales sí aparecen
(`"Japepo Serif", "Source Serif 4", Charter, Georgia, serif`): ahí no nombran al
recorte sino a la fuente original, si el visitante la tiene instalada.

El texto completo de la SIL OFL 1.1 está en https://openfontlicense.org

## Los tuits

Los tuits citados en la sección «Dónde seguirlo» se guardan en
`data/tuits.json` con su identificador, su autor y su fecha, y el enlace lleva
al original en x.com. La página **no** carga nada de x.com por su cuenta: no hay
guion de terceros, no hay incrustado, y nadie queda registrado por X por el solo
hecho de abrir esta página. Quien quiera ver el original aprieta el enlace y
sale de acá.

## Las fuentes periodísticas

Cada dato publicado lleva el identificador de la fuente que lo sostiene, y esas
fuentes están en `data/fuentes.json` con medio, título, URL y fecha de consulta.
Los enlaces van a la nota original. No se reproduce el texto de ninguna nota:
se resume el hecho y se enlaza.

## El programa

«MasterChef» y «MasterChef Celebrity» son marcas de sus dueños. Ver
[LICENCIA.md](LICENCIA.md).
