# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
Recorta las tipografias y las mete adentro del HTML como data URI.

Por que incrustadas: la regla de esta pagina es que no pide un solo archivo a
ningun servidor, ni siquiera al propio. Asi funciona abriendo el archivo desde
el disco, sin red, y nadie queda registrado por leerla.

Por que recortadas: las tres familias completas pesan 800 kB. La pagina usa
unos doscientos signos, y ninguno mas va a aparecer sin que alguien lo escriba
en data/. Recortadas quedan en una decima parte.

Las tres, con su trabajo:

  Be Vietnam Pro   titulares, rotulos y numeros de seccion. Es un grotesco
                   geometrico dibujado para el vietnamita, que lleva las mismas
                   vocales con tilde que el guarani: la i, la e, la o, la u y
                   la y con tilde estan dibujadas, no compuestas al vuelo.
  Source Serif 4   todo lo que se lee de corrido, con eje optico: el cuerpo del
                   texto pide un dibujo y un titular pide otro.
  Source Code      las cifras, que en esta pagina son columnas y tienen que
                   alinearse.

Las tres bajo SIL Open Font License 1.1. El aviso de cada una sale del propio
binario, no de lo que uno se acuerde: ver gui/tipos/OFL-*.txt.

Por que dos de las tres cambian de nombre. Recortar una fuente es modificarla:
la propia licencia define "Modified Version" como cualquier derivado hecho
borrando componentes o cambiando el formato, y el FAQ oficial contesta que si,
que hacer un subconjunto para la web cuenta. Las dos familias de Adobe llevan
nombre reservado ("Source"), y la clausula 3 prohibe usar ese nombre en una
version modificada. La excepcion por equivalencia funcional pide el mismo
inventario de caracteres, y aca se pasa de 1464 glifos a 292. Asi que los
recortes se publican como "Japepo Serif" y "Japepo Mono", que es exactamente lo
que la licencia manda hacer, y el credito a Adobe queda escrito en el pie de la
pagina, en TERCEROS.md y adentro del propio binario. Be Vietnam Pro no lleva
nombre reservado, asi que conserva el suyo.

    python3 gui/fuentes.py

Escribe gui/fuentes.css. Se corre a mano, cuando cambia el juego de signos.
"""

from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
TIPOS = ROOT / "gui" / "tipos"
DESTINO = ROOT / "gui" / "fuentes.css"

# --------------------------------------------------------------------------
# El juego de signos. Generoso a proposito: tiene que aguantar un nombre nuevo
# en data/ sin volver a correr esto. gui/verificar.py comprueba que la pagina
# no use ni un signo que no este aca.
# --------------------------------------------------------------------------
LATIN = "".join(chr(c) for c in range(0x20, 0x7F))
CASTELLANO = "áéíóúÁÉÍÓÚàèìòùÀÈÌÒÙâêîôûÂÊÎÔÛäëïöüÄËÏÖÜñÑçÇ¿¡ºª"
GUARANI = "ãẽĩõũỹÃẼĨÕŨỸýÝÿŸ" + "̃"    # la tilde combinante: g̃ se arma con dos signos.
                                      # La y con acento es guarani tonico: «mboýpa».
TIPOGRAFIA = "«»“”‘’–—…·•±×÷≈≤≥→←↑↓№§¶†‡"
SIGNOS = "₲€$%‰°♥▸▾✓✗★"
CHARSET = LATIN + CASTELLANO + GUARANI + TIPOGRAFIA + SIGNOS

FAMILIAS = [
    {
        "archivo": "BeVietnamPro-Medium.ttf",
        "familia": "Be Vietnam Pro",
        "peso": 500,
        "ejes": None,
    },
    {
        "archivo": "BeVietnamPro-Bold.ttf",
        "familia": "Be Vietnam Pro",
        "peso": 700,
        "ejes": None,
    },
    {
        "archivo": "SourceSerif4Variable.woff2",
        "familia": "Japepo Serif",
        "peso": "250 700",
        # El eje optico se fija en 11: esta familia solo pone texto para leer, y el
        # dibujo de 11 puntos es el que corresponde. Cargar el rango entero, de 8 a
        # 60, cuesta 54 kB de deformaciones que ninguna linea de esta pagina usa.
        "ejes": {"wght": (250, 400, 700), "opsz": 11},
    },
    {
        "archivo": "SourceCodeVariable.woff2",
        "familia": "Japepo Mono",
        "peso": 450,                       # un pelo mas que el redondo: las cifras chicas lo piden
        "ejes": {"wght": 450},
    },
]


def podar_ejes(origen: Path, salida: Path, ejes: dict) -> Path:
    """
    Achica el rango de los ejes antes de recortar los signos.

    Una variable trae una deformacion por cada eje y por cada punto de cada
    contorno. Source Serif entera, con el peso de 200 a 900 y el eje optico de
    8 a 60, pesa 98 kB recortada; podada a lo que la pagina usa de verdad baja
    a la mitad. Es la parte del archivo que nadie ve y que igual se descarga.
    """
    from fontTools.varLib import instancer

    f = TTFont(origen, fontNumber=0)
    instancer.instantiateVariableFont(f, ejes, inplace=True, updateFontNames=False)
    f.flavor = None
    f.save(salida)
    return salida


def recortar(origen: Path, salida: Path, ejes: dict | None) -> None:
    fuente = origen
    temporal = None
    if ejes:
        temporal = TIPOS / f".podada-{origen.stem}.ttf"
        fuente = podar_ejes(origen, temporal, ejes)
    orden = [
        str(fuente),
        f"--text={CHARSET}",
        "--flavor=woff2",
        f"--output-file={salida}",
        "--layout-features=kern,liga,ccmp,mark,mkmk,tnum,frac",
        "--no-hinting",
        "--desubroutinize",
        "--name-IDs=0,13,14",              # se conserva el aviso de licencia adentro del binario
        "--drop-tables+=DSIG",
    ]
    r = subprocess.run([sys.executable, "-m", "fontTools.subset", *orden],
                       capture_output=True, text=True)
    if temporal and temporal.exists():
        temporal.unlink()
    if r.returncode != 0:
        raise SystemExit(f"no se pudo recortar {origen.name}: {r.stderr.strip()}")


def licencia(origen: Path) -> tuple[str, str]:
    """El aviso sale del binario, no de la memoria de nadie."""
    f = TTFont(origen, fontNumber=0)
    nombres = {r.nameID: str(r) for r in f["name"].names if r.platformID == 3}
    return nombres.get(0, ""), nombres.get(14, "")


def main() -> None:
    bloques, avisos, total = [], [], 0
    for spec in FAMILIAS:
        origen = TIPOS / spec["archivo"]
        recorte = TIPOS / f".recorte-{origen.stem}.woff2"
        recortar(origen, recorte, spec["ejes"])
        datos = recorte.read_bytes()
        recorte.unlink()
        total += len(datos)

        b64 = base64.b64encode(datos).decode()
        peso = spec["peso"]
        bloques.append(
            f'/* {spec["familia"]} {peso} · {origen.name} · {len(datos) / 1024:.1f} kB */\n'
            f'@font-face{{font-family:"{spec["familia"]}";font-style:normal;'
            f'font-weight:{peso};font-display:swap;'
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )
        derechos, url = licencia(origen)
        avisos.append(f"   {spec['familia']:16s} {derechos} · {url}")

    cabecera = (
        "/* ==========================================================================\n"
        "   Tipografia incrustada. La genera gui/fuentes.py; no se edita a mano.\n"
        "\n"
        "   Tres familias con tres trabajos: Be Vietnam Pro para titular y rotulo,\n"
        "   Japepo Serif para lo que se lee de corrido, Japepo Mono para las cifras\n"
        "   que forman columna. Las dos ultimas son recortes de Source Serif 4 y de\n"
        "   Source Code, de Adobe, renombrados porque la OFL no deja usar el nombre\n"
        "   reservado en una version modificada, y recortar es modificar.\n"
        "\n"
        "   Las tres bajo SIL Open Font License 1.1:\n"
        + "\n".join(avisos) + "\n"
        "   ========================================================================== */\n"
    )
    DESTINO.write_text(cabecera + "\n" + "\n\n".join(bloques) + "\n")
    print(f"  ok · {DESTINO.relative_to(ROOT)}")
    print(f"  {len(FAMILIAS)} recortes · {total / 1024:.0f} kB de fuente · "
          f"{len(CHARSET)} signos")


if __name__ == "__main__":
    main()
