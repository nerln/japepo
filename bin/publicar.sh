#!/bin/sh
# Rehace, comprueba y publica. Sin preguntar nada.
#
# Es el camino entero en un comando: recalcular el pronóstico con los datos que
# haya en data/, escribir la corrida en el registro, rearmar la página y la
# tarjeta, pasar las dieciocho comprobaciones y empujar. Si alguna falla NO
# publica y sale con error, que es la única forma de que esto pueda correr solo
# sin que nadie lo mire.
#
#   bin/publicar.sh                       recalcula todo y publica
#   bin/publicar.sh --gala 5              además congela la promesa para la gala 5
#   bin/publicar.sh --social              vuelve a medir vistas y comentarios
#   bin/publicar.sh --solo-web            no recalcula el modelo, sólo rearma la página
#   bin/publicar.sh --sin-empujar         deja el commit hecho y no lo manda
#
# Correr desde cualquier lado: se ubica solo.

set -eu

cd "$(dirname "$0")/.."

SOLO_WEB=0
EMPUJAR=1
SOCIAL=0
GALA=""
FECHA=$(date +%Y-%m-%d)

while [ $# -gt 0 ]; do
  case "$1" in
    --solo-web)    SOLO_WEB=1 ;;
    --social)      SOCIAL=1 ;;
    --sin-empujar) EMPUJAR=0 ;;
    --gala)        shift; GALA="$1" ;;
    --fecha)       shift; FECHA="$1" ;;
    *) echo "no conozco la opción $1" >&2; exit 2 ;;
  esac
  shift
done

corre() { echo ">>> $*"; "$@"; }

# Las vistas se miden solo si se pide: son treinta pedidos a YouTube y tardan
# unos minutos. El resto de la corrida no las necesita para nada.
if [ "$SOCIAL" -eq 1 ]; then
  corre python3 model/social.py --fecha "$FECHA"
fi

if [ "$SOLO_WEB" -eq 0 ]; then
  corre python3 model/preparacion.py
  if [ -n "$GALA" ]; then
    corre python3 model/registrar.py --fecha "$FECHA" --gala "$GALA"
  else
    corre python3 model/registrar.py --fecha "$FECHA"
  fi
fi

# El orden importa: registrar.py escribe en data/, y la firma de la corrida es
# un hash de data/, así que la página se arma después.
corre python3 gui/build.py   >/dev/null
corre python3 gui/tarjeta.py >/dev/null

# El portero. Si esto falla no se publica, y el guion termina en error para que
# quien lo haya lanzado se entere aunque nadie esté mirando.
if ! python3 gui/verificar.py; then
  echo "no se publica: alguna comprobación falló" >&2
  exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "nada que publicar: el árbol está limpio"
  exit 0
fi

CORRIDA=$(python3 -c 'import sys;sys.path.insert(0,"gui");from firma import firma_corrida;print(firma_corrida())')
git add -A
git commit -q -m "corrida $CORRIDA" \
  -m "Publicado por bin/publicar.sh tras pasar las comprobaciones." \
  -m "Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
echo "commit de la corrida $CORRIDA"

if [ "$EMPUJAR" -eq 1 ]; then
  git push
  echo "empujado. el despliegue tarda un par de minutos: gh run list --limit 1"
else
  echo "sin empujar, como se pidió"
fi
