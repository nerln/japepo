# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
Una figura por persona, generada, sin ninguna foto.

Las fotos de los participantes son de la produccion y de ellos. Republicarlas
para ilustrar un analisis que nadie les pidio no hace falta y no corresponde,
asi que cada persona entra con una figura dibujada a partir de su nombre:
iniciales, un tono estable y un arco en un angulo propio. El mismo nombre da
siempre la misma figura, y ninguna figura dice nada de nadie.
"""

from __future__ import annotations

import hashlib
import math

LADO = 64


def _semilla(texto: str) -> int:
    return int(hashlib.sha256(texto.encode()).hexdigest()[:8], 16)


def iniciales(nombre: str) -> str:
    partes = [p for p in nombre.replace(".", " ").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def svg(nombre: str, id_: str, destacado: bool = False) -> str:
    s = _semilla(id_)
    tono = s % 360
    giro = (s >> 9) % 360
    letras = iniciales(nombre)

    r = 26
    g0 = math.radians(giro)
    g1 = math.radians(giro + 96)
    x0, y0 = LADO / 2 + r * math.cos(g0), LADO / 2 + r * math.sin(g0)
    x1, y1 = LADO / 2 + r * math.cos(g1), LADO / 2 + r * math.sin(g1)

    anillo = (
        f'<path d="M {x0:.2f} {y0:.2f} A {r} {r} 0 0 1 {x1:.2f} {y1:.2f}" '
        f'stroke="hsl({tono} 55% 72%)" stroke-width="4" fill="none" stroke-linecap="round"/>'
    )
    corona = (
        f'<circle cx="{LADO / 2}" cy="{LADO / 2}" r="30" fill="none" '
        f'stroke="var(--destacado)" stroke-width="2.5" stroke-dasharray="3 4"/>'
        if destacado else ""
    )
    return (
        f'<svg viewBox="0 0 {LADO} {LADO}" class="cara" aria-hidden="true" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{LADO / 2}" cy="{LADO / 2}" r="22" fill="hsl({tono} 38% 34%)"/>'
        f'{anillo}{corona}'
        f'<text x="{LADO / 2}" y="{LADO / 2}" text-anchor="middle" dominant-baseline="central" '
        f'font-size="17" font-weight="600" fill="#fff" letter-spacing="0.5">{letras}</text>'
        f"</svg>"
    )


if __name__ == "__main__":
    print(svg("Joaquín Serrano", "joaquin", destacado=True))
