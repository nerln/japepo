# SPDX-FileCopyrightText: 2026 nerln <https://github.com/nerln>
# SPDX-License-Identifier: Apache-2.0
"""
Guarda el pronostico del dia en data/historial_pronostico.json.

Un pronostico que se puede reescribir despues de conocer el resultado no es un
pronostico. Cada corrida deja fecha, cuantas galas habian pasado, quien puntea,
con cuanto, y cuanta ignorancia quedaba. Dentro de dos meses eso se puede leer
contra lo que efectivamente paso.

Es idempotente por fecha: correrlo dos veces el mismo dia pisa la entrada de
ese dia y no agrega una nueva.

    python3 model/registrar.py [--fecha AAAA-MM-DD]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DESTINO = DATA / "historial_pronostico.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", required=True, help="AAAA-MM-DD, la fecha de la corrida")
    args = ap.parse_args()

    stats = json.loads((DATA / "estadisticas.json").read_text())
    base = stats["escenarios"]["base"]
    lider = max(base["p_gana"], key=base["p_gana"].get)

    entrada = {
        "fecha": args.fecha,
        "galas": stats["galas_jugadas"],
        "eliminados": stats["eliminados"],
        "lider": lider,
        "p_lider": base["p_gana"][lider],
        "p_lider_ee": base["p_gana_ee"][lider],
        "ignorancia": base["ignorancia"],
        "semilla": stats["semilla"],
    }

    if DESTINO.exists():
        historial = json.loads(DESTINO.read_text())
    else:
        historial = {
            "_nota": ("Un pronostico por corrida, con fecha. No se edita hacia atras: "
                      "si una entrada envejece mal, envejece mal a la vista."),
            "entradas": [],
        }

    entradas = [e for e in historial["entradas"] if e["fecha"] != args.fecha]
    entradas.append(entrada)
    historial["entradas"] = sorted(entradas, key=lambda e: e["fecha"])
    DESTINO.write_text(json.dumps(historial, ensure_ascii=False, indent=2) + "\n")

    print(f"  ok · {DESTINO.relative_to(ROOT)} · {len(historial['entradas'])} entradas")


if __name__ == "__main__":
    main()
