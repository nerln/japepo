# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
La tarjeta de previsualizacion: lo que se ve cuando alguien comparte el enlace.

Una pagina sobre un programa de television se comparte por WhatsApp y por X, y
sin tarjeta el enlace llega como una linea de texto gris. Esta lleva lo unico
que hace falta para decidir si abrirla: cuando es la proxima gala y quien va
adelante.

Se dibuja con las mismas tipografias que la pagina y con los mismos datos, y
sale igual byte a byte en cada corrida: nada de fechas del reloj del sistema,
nada de aleatoriedad. Por eso gui/verificar.py la puede reconstruir y comparar,
igual que el HTML. Publicar una tarjeta vieja hace fallar la verificacion.

    python3 gui/tarjeta.py

Escribe web/og.png (1200x630) y web/icono.svg.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
TIPOS = ROOT / "gui" / "tipos"
sys.path.insert(0, str(ROOT / "gui"))

ANCHO, ALTO = 1200, 630
MARGEN = 72

# El tema claro de la pagina, escrito una vez mas porque una imagen no lee CSS.
FONDO = (250, 247, 242)
TEXTO = (27, 23, 20)
SUAVE = (107, 97, 87)
ACENTO = (181, 69, 31)
BORDE = (226, 217, 203)


def tipo(nombre: str, cuerpo: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(TIPOS / nombre), cuerpo)


def olla(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, probs: list[float]) -> None:
    """La misma marca que la pagina: el borde partido en tantos arcos como personas."""
    total = sum(probs) or 1.0
    hueco = 2.2
    disponible = 360.0 - hueco * len(probs)
    cursor = -90.0
    caja = (cx - r, cy - r, cx + r, cy + r)
    d.ellipse((cx - r + 11, cy - r + 11, cx + r - 11, cy + r - 11), fill=(239, 228, 211))
    for p in probs:
        ancho = disponible * (p / total)
        d.arc(caja, cursor, cursor + ancho, fill=ACENTO, width=11)
        cursor += ancho + hueco
    # el remolino de revolver, como en la marca de la pagina
    import math
    puntos = []
    for paso in range(141):
        f = paso / 140
        ang = math.radians(-90 + f * 540)
        rr = 6 + f * (r - 24)
        puntos.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.line(puntos, fill=(138, 109, 31), width=3, joint="curve")


def main() -> None:
    from build import contexto, cargar, emisiones, pct        # noqa: PLC0415

    d = cargar()
    base = d["stats"]["escenarios"]["base"]["p_gana"]
    nombres = {p["id"]: p["nombre"] for p in d["plantel"]["plantel"]}
    orden = sorted(base, key=base.get, reverse=True)[:3]
    prox = emisiones(d)[0]

    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d_ = ImageDraw.Draw(img)

    d_.rectangle((0, 0, ANCHO, 8), fill=ACENTO)
    olla(d_, ANCHO - MARGEN - 96, MARGEN + 96, 96, sorted(base.values(), reverse=True))

    d_.text((MARGEN, MARGEN), "SEGUNDA TEMPORADA · SNT",
            font=tipo("BeVietnamPro-Medium.ttf", 22), fill=ACENTO)
    d_.text((MARGEN, MARGEN + 40), "MasterChef Celebrity",
            font=tipo("BeVietnamPro-Bold.ttf", 66), fill=TEXTO)
    d_.text((MARGEN, MARGEN + 112), "Paraguay 2026",
            font=tipo("BeVietnamPro-Bold.ttf", 66), fill=TEXTO)

    y = MARGEN + 214
    d_.text((MARGEN, y), "PRÓXIMA GALA", font=tipo("BeVietnamPro-Medium.ttf", 20), fill=SUAVE)
    d_.text((MARGEN, y + 28), f"{prox['es']}, {d['programa']['hora']}",
            font=tipo("BeVietnamPro-Bold.ttf", 38), fill=TEXTO)

    y += 96
    d_.line((MARGEN, y, ANCHO - MARGEN, y), fill=BORDE, width=1)
    y += 22
    d_.text((MARGEN, y), "QUIÉN TIENE MÁS CHANCES",
            font=tipo("BeVietnamPro-Medium.ttf", 20), fill=SUAVE)
    y += 32
    for pid in orden:
        d_.text((MARGEN, y), nombres[pid], font=tipo("BeVietnamPro-Bold.ttf", 30), fill=TEXTO)
        etiqueta = f"{pct(base[pid])} %"
        f = tipo("BeVietnamPro-Medium.ttf", 30)
        d_.text((ANCHO - MARGEN - d_.textlength(etiqueta, font=f), y), etiqueta, font=f, fill=ACENTO)
        y += 44

    pie = "nerln.github.io/japepo · castellano ha guaraní · sin relación con la producción"
    d_.text((MARGEN, ALTO - 44), pie,
            font=tipo("BeVietnamPro-Medium.ttf", 20), fill=SUAVE)

    WEB.mkdir(exist_ok=True)
    img.save(WEB / "og.png", optimize=True)

    # El icono de la pestana: la misma olla, vectorial, sin mapa de bits.
    from marca import svg as marca_svg                        # noqa: PLC0415
    icono = marca_svg(sorted(base.values(), reverse=True), "japepo")
    icono = icono.replace("var(--marca-anillo)", "#b5451f")
    icono = icono.replace("var(--marca-caldo)", "#efe4d3")
    icono = icono.replace("var(--marca-vapor)", "#8a6d1f")
    icono = icono.replace(' class="marca"', "")
    (WEB / "icono.svg").write_text(icono + "\n")

    print(f"  ok · web/og.png ({(WEB / 'og.png').stat().st_size / 1024:.0f} kB)")
    print(f"  ok · web/icono.svg ({(WEB / 'icono.svg').stat().st_size / 1024:.1f} kB)")


if __name__ == "__main__":
    main()
