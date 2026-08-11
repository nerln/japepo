# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
La marca de la pagina: un japepo visto desde arriba.

Que NO es: el logotipo de MasterChef. Ese logotipo es marca registrada de
Banijay y no se calca, ni se redibuja, ni se aproxima. Nombrar el programa para
decir de que trata el analisis es legitimo; usar su identidad como identidad
propia, no.

Que si es: la boca de una olla. El anillo del borde esta partido en tantos arcos
como personas quedan en competencia, cada uno del largo de su probabilidad de
ganar. Hoy los dieciocho arcos son casi iguales, y esa es exactamente la lectura
de la pagina. Se redibuja despues de cada gala, asi que el borde se va rompiendo
en pedazos desparejos a medida que la temporada separa a la gente.

Los colores salen de variables CSS: la marca cambia con el tema.
"""

from __future__ import annotations

import math

LADO = 128
CENTRO = LADO / 2
R_ANILLO = 52.0
GROSOR = 9.0
HUECO_GRADOS = 2.2          # aire entre arcos, para que se cuenten a simple vista


def _arco(r: float, g0: float, g1: float) -> str:
    x0 = CENTRO + r * math.cos(math.radians(g0))
    y0 = CENTRO + r * math.sin(math.radians(g0))
    x1 = CENTRO + r * math.cos(math.radians(g1))
    y1 = CENTRO + r * math.sin(math.radians(g1))
    largo = 1 if (g1 - g0) % 360 > 180 else 0
    return f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {largo} 1 {x1:.2f} {y1:.2f}"


def svg(probabilidades: list[float], titulo: str = "") -> str:
    """probabilidades: una por persona en competencia, en el orden que se quiera dibujar."""
    total = sum(probabilidades) or 1.0
    partes = [p / total for p in probabilidades]
    n = len(partes)
    hueco = HUECO_GRADOS if n > 1 else 0.0
    disponible = 360.0 - hueco * n

    piezas = []
    cursor = -90.0
    for i, parte in enumerate(partes):
        ancho = disponible * parte
        opacidad = 0.45 + 0.55 * (parte * n)      # 1.0 si es la media exacta
        piezas.append(
            f'<path d="{_arco(R_ANILLO, cursor, cursor + ancho)}" '
            f'stroke="var(--marca-anillo)" stroke-width="{GROSOR}" fill="none" '
            f'stroke-linecap="butt" opacity="{min(opacidad, 1.0):.3f}"/>'
        )
        cursor += ancho + hueco

    # el remolino de revolver: una espiral, no vapor. La olla se ve desde arriba.
    puntos = []
    for paso in range(0, 141):
        t = paso / 140
        ang = math.radians(-90 + t * 540)
        r = 4 + t * (R_ANILLO - GROSOR / 2 - 12)
        puntos.append(f"{CENTRO + r * math.cos(ang):.2f} {CENTRO + r * math.sin(ang):.2f}")
    espiral = [
        f'<path d="M {puntos[0]} L ' + " L ".join(puntos[1:]) + '" '
        f'stroke="var(--marca-vapor)" stroke-width="2.2" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
    ]

    return (
        f'<svg viewBox="0 0 {LADO} {LADO}" role="img" aria-label="{titulo}" '
        f'class="marca" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{CENTRO}" cy="{CENTRO}" r="{R_ANILLO - GROSOR / 2 - 3:.1f}" '
        f'fill="var(--marca-caldo)"/>'
        + "".join(piezas)
        + f'<circle cx="{CENTRO - R_ANILLO - 4:.1f}" cy="{CENTRO}" r="4.5" '
          f'fill="var(--marca-anillo)" opacity="0.8"/>'
        + f'<circle cx="{CENTRO + R_ANILLO + 4:.1f}" cy="{CENTRO}" r="4.5" '
          f'fill="var(--marca-anillo)" opacity="0.8"/>'
        + "".join(espiral)
        + "</svg>"
    )


if __name__ == "__main__":
    print(svg([1 / 18] * 18, "japepo"))
